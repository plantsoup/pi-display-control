"""
Multi-Pi Node Discovery, Remote Proxy, Display Dispatch, Broadcast, and Media Sync Service.
Enables connecting and controlling multiple Raspberry Pi instances running Pi Display Control
(e.g., Main Pi at pi.spear.ac and Secondary Pi at pi2.spear.ac).
"""

import os
import re
import ssl
import json
import time
import uuid
import mimetypes
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from display import (
    get_connected_monitors,
    apply_monitor_rotation,
    apply_display_rotations
)
from .storage import (
    UPLOAD_FOLDER,
    LEGACY_UPLOADS,
    load_websites,
    load_images,
    load_schedules,
    load_slideshow_config,
    load_nodes_config,
    save_nodes_config,
    get_monitor_rotation,
    ROTATION_METADATA
)
from .display_service import display_state, trigger_display_action

USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) PiDisplayControl/2.0"
PROXY_HOP_HEADER = "X-Pi-Proxy-Hop"

_PRIVATE_HOST_RE = re.compile(
    r"^(localhost|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|.*\.local)$",
    re.IGNORECASE
)


def _is_local_or_lan_host(host_part):
    """Return True if host looks like localhost, private LAN IP, .local mDNS, or has an explicit non-443 port."""
    if not host_part:
        return False
    if ":" in host_part:
        _, _, port_str = host_part.rpartition(":")
        if port_str != "443":
            return True
    hostname_only = host_part.split(":")[0]
    return bool(_PRIVATE_HOST_RE.match(hostname_only))


def normalize_node_url(raw_url):
    """
    Normalize a user-provided Pi hostname or URL into a clean base URL (no trailing slash).
    Examples:
      - 'pi2.spear.ac' -> 'https://pi2.spear.ac'
      - 'https://pi2.spear.ac/' -> 'https://pi2.spear.ac'
      - '192.168.1.50:5000' -> 'http://192.168.1.50:5000'
      - 'http://pi2.local:5001/api/status' -> 'http://pi2.local:5001'
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("Pi hostname or URL is required")

    cleaned = raw_url.strip()
    if not cleaned:
        raise ValueError("Pi hostname or URL is required")

    has_scheme = "://" in cleaned
    if not has_scheme:
        first_segment = cleaned.split("/")[0]
        default_scheme = "http" if _is_local_or_lan_host(first_segment) else "https"
        cleaned = f"{default_scheme}://{cleaned}"

    parsed = urllib.parse.urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Use http:// or https://")

    if not parsed.hostname:
        raise ValueError(f"Invalid hostname in URL '{raw_url}'")

    # Strip accidental endpoint suffixes if user pasted /api/status or /viewer
    path = (parsed.path or "").rstrip("/")
    for suffix in ("/api/status", "/api/display/monitors", "/api", "/viewer", "/slideshow"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break

    base = f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")
    return base


def build_discovery_candidates(raw_url):
    """Generate ordered candidate base URLs when auto-discovering a Pi node."""
    primary = normalize_node_url(raw_url)
    candidates = [primary]

    raw_trimmed = (raw_url or "").strip()
    has_explicit_scheme = "://" in raw_trimmed
    parsed = urllib.parse.urlparse(primary)
    host = parsed.hostname
    has_explicit_port = parsed.port is not None

    if not has_explicit_scheme and host:
        if has_explicit_port:
            alt_scheme = "https" if parsed.scheme == "http" else "http"
            alt = f"{alt_scheme}://{host}:{parsed.port}"
            if alt not in candidates:
                candidates.append(alt)
        else:
            extras = [
                f"https://{host}",
                f"http://{host}",
                f"http://{host}:5001",
                f"http://{host}:5000"
            ]
            for ex in extras:
                if ex not in candidates:
                    candidates.append(ex)

    return candidates


def is_self_node(node_url, request_host=None):
    """
    Detect whether node_url points back to the currently serving host to prevent self-proxy loops.
    """
    if not node_url or not request_host:
        return False
    try:
        parsed = urllib.parse.urlparse(normalize_node_url(node_url))
        req_host_clean = request_host.strip().lower()
        node_netloc = (parsed.netloc or "").lower()

        if node_netloc == req_host_clean:
            return True

        req_hostname = req_host_clean.split(":")[0]
        req_port = req_host_clean.split(":")[1] if ":" in req_host_clean else None
        node_hostname = (parsed.hostname or "").lower()
        node_port = str(parsed.port) if parsed.port else None

        # Match bare domain behind reverse proxy (ports 80/443 omitted in Host header)
        if node_hostname == req_hostname and node_port is None and req_port in (None, "80", "443"):
            return True
    except Exception:
        return False
    return False


def get_node_by_id(node_id):
    """Retrieve a node configuration dict by id ('local' or remote node id)."""
    cfg = load_nodes_config()
    if node_id == "local":
        local_node = dict(cfg["local"])
        local_node["is_local"] = True
        local_node["enabled"] = True
        return local_node

    for n in cfg.get("nodes", []):
        if n.get("id") == node_id:
            node_copy = dict(n)
            node_copy["is_local"] = False
            return node_copy
    return None


def resolve_public_base_url(request_host_url=None):
    """
    Resolve Main/Local Pi's network-reachable base URL so remote Pis can stream
    /viewer slideshows and images directly in Chromium kiosk mode.
    """
    cfg = load_nodes_config()
    configured_url = (cfg.get("local", {}).get("url") or "").strip().rstrip("/")

    # If request came in on a real network host (not 127.0.0.1/localhost), prefer configured URL or request_host_url
    if request_host_url:
        req_clean = request_host_url.strip().rstrip("/")
        try:
            parsed_req = urllib.parse.urlparse(req_clean)
            if parsed_req.hostname and parsed_req.hostname not in ("127.0.0.1", "localhost"):
                if not configured_url:
                    return req_clean
        except Exception:
            pass

    if configured_url:
        try:
            return normalize_node_url(configured_url)
        except ValueError:
            pass

    if request_host_url:
        return request_host_url.strip().rstrip("/")
    return "https://pi.spear.ac"


def _build_ssl_context(verify_ssl=True):
    if verify_ssl:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def remote_request(
    node_or_url,
    method="GET",
    path="/api/status",
    query_string=b"",
    body=None,
    content_type="application/json",
    timeout=6.0,
    verify_ssl=True,
    api_key=""
):
    """
    Execute an HTTP/HTTPS request against a remote Pi Display Control instance.
    Returns tuple: (transport_ok, status_code, resp_bytes, resp_content_type, error_msg, latency_ms)
    """
    if isinstance(node_or_url, dict):
        base_url = node_or_url.get("url", "")
        verify_ssl = bool(node_or_url.get("verify_ssl", True))
        api_key = node_or_url.get("api_key", "") or ""
    else:
        base_url = str(node_or_url)

    try:
        clean_base = normalize_node_url(base_url)
    except ValueError as e:
        return False, 400, b"", "application/json", str(e), 0

    clean_path = path if path.startswith("/") else f"/{path}"
    full_url = f"{clean_base}{clean_path}"
    if query_string:
        qs_str = query_string.decode("utf-8", errors="replace") if isinstance(query_string, bytes) else str(query_string)
        qs_str = qs_str.lstrip("?")
        if qs_str:
            full_url = f"{full_url}?{qs_str}"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, */*",
        PROXY_HOP_HEADER: "1"
    }
    if content_type and body is not None:
        headers["Content-Type"] = content_type
    if api_key:
        headers["X-Pi-Api-Key"] = api_key

    req = urllib.request.Request(full_url, data=body, headers=headers, method=method.upper())
    ssl_ctx = _build_ssl_context(verify_ssl=verify_ssl) if full_url.startswith("https://") else None

    start_ts = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            latency_ms = int(round((time.monotonic() - start_ts) * 1000))
            resp_bytes = resp.read()
            resp_ct = resp.headers.get("Content-Type", "application/json")
            return True, resp.status, resp_bytes, resp_ct, None, latency_ms
    except urllib.error.HTTPError as e:
        latency_ms = int(round((time.monotonic() - start_ts) * 1000))
        try:
            err_body = e.read()
        except Exception:
            err_body = b""
        resp_ct = e.headers.get("Content-Type", "application/json") if e.headers else "application/json"
        return True, e.code, err_body, resp_ct, f"HTTP {e.code}: {e.reason}", latency_ms
    except urllib.error.URLError as e:
        latency_ms = int(round((time.monotonic() - start_ts) * 1000))
        reason = getattr(e, "reason", str(e))
        return False, 502, b"", "application/json", f"Connection failed: {reason}", latency_ms
    except Exception as e:
        latency_ms = int(round((time.monotonic() - start_ts) * 1000))
        return False, 502, b"", "application/json", f"Request error: {str(e)}", latency_ms


def get_local_monitors_list():
    """Build local monitor list and defaults matching /api/display/monitors."""
    connected = get_connected_monitors()
    defaults = {
        "1": get_monitor_rotation("1", "left"),
        "2": get_monitor_rotation("2", "right")
    }
    monitors_data = []
    for idx, m in enumerate(connected, 1):
        mon_idx_str = str(idx)
        m_copy = dict(m)
        m_copy["index"] = idx
        m_copy["current_rotation"] = m.get("rotation", "normal")
        m_copy["default_rotation"] = defaults.get(mon_idx_str, "normal")
        monitors_data.append(m_copy)

    if not monitors_data:
        monitors_data = [
            {
                "index": 1,
                "name": "HDMI-1 (Primary)",
                "primary": True,
                "current_rotation": defaults.get("1", "left"),
                "default_rotation": defaults.get("1", "left"),
                "width": 1080 if defaults.get("1", "left") in ["left", "right"] else 1920,
                "height": 1920 if defaults.get("1", "left") in ["left", "right"] else 1080,
                "connected": False
            },
            {
                "index": 2,
                "name": "HDMI-2 (Secondary)",
                "primary": False,
                "current_rotation": defaults.get("2", "right"),
                "default_rotation": defaults.get("2", "right"),
                "width": 1080 if defaults.get("2", "right") in ["left", "right"] else 1920,
                "height": 1920 if defaults.get("2", "right") in ["left", "right"] else 1080,
                "connected": False
            }
        ]
    return monitors_data, len(connected), defaults


def get_local_node_overview():
    """Return full runtime status and monitor inventory for this local Pi."""
    cfg = load_nodes_config()
    local_meta = cfg["local"]
    schedules = load_schedules()
    images = load_images()
    websites = load_websites()
    monitors_data, physical_count, defaults = get_local_monitors_list()

    return {
        "id": "local",
        "name": local_meta.get("name", "Main Pi"),
        "url": local_meta.get("url", "https://pi.spear.ac"),
        "role": local_meta.get("role", "main"),
        "is_local": True,
        "enabled": True,
        "online": True,
        "latency_ms": 0,
        "error": None,
        "state": dict(display_state),
        "counts": {
            "websites": len(websites),
            "images": len(images),
            "schedules": len(schedules),
            "active_schedules": len([s for s in schedules if s.get("enabled", True)])
        },
        "monitors": monitors_data,
        "monitor_count": len(monitors_data),
        "physical_monitor_count": physical_count,
        "defaults": defaults,
        "available_rotations": ROTATION_METADATA,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def _probe_single_url(url, verify_ssl=True, api_key="", timeout=3.5):
    """Probe a single candidate base URL for Pi Display Control /api/status and /api/display/monitors."""
    ok, status_code, body, _, err, latency_ms = remote_request(
        url,
        method="GET",
        path="/api/status",
        timeout=timeout,
        verify_ssl=verify_ssl,
        api_key=api_key
    )
    if not ok or status_code != 200:
        return {
            "online": False,
            "resolved_url": url,
            "latency_ms": latency_ms,
            "error": err or f"Unexpected HTTP status {status_code}"
        }

    try:
        status_json = json.loads(body.decode("utf-8"))
    except Exception:
        return {
            "online": False,
            "resolved_url": url,
            "latency_ms": latency_ms,
            "error": "Host responded, but not with valid Pi Display Control JSON"
        }

    if not isinstance(status_json, dict) or not status_json.get("success") or "state" not in status_json:
        return {
            "online": False,
            "resolved_url": url,
            "latency_ms": latency_ms,
            "error": "Host is online, but does not appear to be running Pi Display Control"
        }

    # Fetch monitors information as well
    monitors = []
    defaults = {"1": "normal", "2": "normal"}
    physical_count = 0
    ok_m, m_code, m_body, _, _, _ = remote_request(
        url,
        method="GET",
        path="/api/display/monitors",
        timeout=timeout,
        verify_ssl=verify_ssl,
        api_key=api_key
    )
    if ok_m and m_code == 200:
        try:
            m_json = json.loads(m_body.decode("utf-8"))
            if isinstance(m_json, dict) and m_json.get("success"):
                monitors = m_json.get("monitors", [])
                physical_count = m_json.get("count", len(monitors))
                defaults = m_json.get("defaults", defaults)
        except Exception:
            pass

    return {
        "online": True,
        "resolved_url": url,
        "latency_ms": latency_ms,
        "error": None,
        "state": status_json.get("state", {}),
        "counts": status_json.get("counts", {}),
        "server_time": status_json.get("server_time"),
        "monitors": monitors,
        "monitor_count": len(monitors),
        "physical_monitor_count": physical_count,
        "defaults": defaults
    }


def probe_node(raw_url, verify_ssl=True, api_key="", auto_discover=False, timeout=3.5):
    """
    Verify connectivity to a remote Pi Display Control server and discover its monitors.
    When auto_discover=True, tries fallback schemes/ports if no explicit scheme was provided.
    """
    candidates = build_discovery_candidates(raw_url) if auto_discover else [normalize_node_url(raw_url)]
    first_result = None

    for candidate in candidates:
        res = _probe_single_url(candidate, verify_ssl=verify_ssl, api_key=api_key, timeout=timeout)
        if first_result is None:
            first_result = res
        if res.get("online"):
            return res

    return first_result or {
        "online": False,
        "resolved_url": normalize_node_url(raw_url),
        "latency_ms": 0,
        "error": "Unable to reach Pi Display Control instance"
    }


def _build_remote_node_overview(node, request_host=None, timeout=3.5):
    """Assemble overview object for a configured remote node."""
    base_info = {
        "id": node.get("id"),
        "name": node.get("name", "Connected Pi"),
        "url": node.get("url", ""),
        "role": node.get("role", "secondary"),
        "is_local": False,
        "enabled": bool(node.get("enabled", True)),
        "verify_ssl": bool(node.get("verify_ssl", True)),
        "has_api_key": bool(node.get("api_key")),
        "online": False,
        "latency_ms": None,
        "error": None,
        "state": None,
        "counts": None,
        "monitors": [],
        "monitor_count": 0,
        "physical_monitor_count": 0,
        "defaults": {"1": "normal", "2": "normal"}
    }

    if not base_info["enabled"]:
        base_info["error"] = "Disabled"
        return base_info

    if is_self_node(base_info["url"], request_host=request_host):
        local_ov = get_local_node_overview()
        base_info.update({
            "is_self_alias": True,
            "online": True,
            "latency_ms": 0,
            "state": local_ov["state"],
            "counts": local_ov["counts"],
            "monitors": local_ov["monitors"],
            "monitor_count": local_ov["monitor_count"],
            "physical_monitor_count": local_ov["physical_monitor_count"],
            "defaults": local_ov["defaults"]
        })
        return base_info

    probe_res = _probe_single_url(
        base_info["url"],
        verify_ssl=base_info["verify_ssl"],
        api_key=node.get("api_key", ""),
        timeout=timeout
    )
    base_info.update({
        "online": probe_res.get("online", False),
        "latency_ms": probe_res.get("latency_ms"),
        "error": probe_res.get("error"),
        "state": probe_res.get("state"),
        "counts": probe_res.get("counts"),
        "server_time": probe_res.get("server_time"),
        "monitors": probe_res.get("monitors", []),
        "monitor_count": probe_res.get("monitor_count", 0),
        "physical_monitor_count": probe_res.get("physical_monitor_count", 0),
        "defaults": probe_res.get("defaults", {"1": "normal", "2": "normal"})
    })
    return base_info


def get_all_nodes_overview(request_host=None, timeout=3.5):
    """
    Gather live status and display/monitor data for Local Pi + all configured Remote Pis concurrently.
    """
    cfg = load_nodes_config()
    local_overview = get_local_node_overview()
    remote_nodes = cfg.get("nodes", [])

    if not remote_nodes:
        return [local_overview]

    ordered_remotes = [None] * len(remote_nodes)
    max_workers = min(8, max(1, len(remote_nodes)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_build_remote_node_overview, n, request_host, timeout): idx
            for idx, n in enumerate(remote_nodes)
        }
        for fut in as_completed(future_map):
            idx = future_map[fut]
            try:
                ordered_remotes[idx] = fut.result()
            except Exception as e:
                n = remote_nodes[idx]
                ordered_remotes[idx] = {
                    "id": n.get("id"),
                    "name": n.get("name", "Connected Pi"),
                    "url": n.get("url", ""),
                    "role": n.get("role", "secondary"),
                    "is_local": False,
                    "enabled": bool(n.get("enabled", True)),
                    "online": False,
                    "error": str(e),
                    "monitors": [],
                    "monitor_count": 0
                }

    # Filter out self-alias duplicates if running directly on pi2.spear.ac with default config
    results = [local_overview]
    for r in ordered_remotes:
        if r and not r.get("is_self_alias"):
            results.append(r)
    return results


def _build_main_viewer_url(main_base_url, monitor_id="1", mode="random", interval=30, fit="cover", single_image=None):
    """Build a full URL pointing to Main Pi's /viewer endpoint for remote Chromium kiosk streaming."""
    base = (main_base_url or "https://pi.spear.ac").rstrip("/")
    fit_clean = fit if fit in ("cover", "contain") else "cover"
    if single_image:
        enc_img = urllib.parse.quote(str(single_image))
        return f"{base}/viewer?single={enc_img}&monitor={monitor_id}&fit={fit_clean}"
    clean_mode = mode if mode in ("random", "sequential") else "random"
    return f"{base}/viewer?monitor={monitor_id}&mode={clean_mode}&interval={int(interval or 30)}&fit={fit_clean}"


def prepare_remote_display_payload(payload, main_base_url):
    """
    Transform display payload for a remote Pi node.
    Translates 'main_slideshow', 'main_image', or 'stream_from_main=True' targets into
    fullscreen kiosk URLs streaming from Main Pi (e.g., https://pi.spear.ac/viewer?...).
    """
    data = dict(payload or {})
    stream_from_main = bool(data.pop("stream_from_main", False))
    slideshow_cfg = load_slideshow_config()
    default_fit = data.get("fit") or slideshow_cfg.get("fit", "cover")
    default_mode = data.get("slideshow_mode") or (
        data.get("mode") if data.get("mode") in ("random", "sequential") else slideshow_cfg.get("mode", "random")
    )
    default_interval = data.get("interval") or slideshow_cfg.get("interval", 30)

    def _transform_target(target, mon_id):
        if not isinstance(target, dict):
            return target
        t = target.get("type", "website")
        item_fit = target.get("fit") or default_fit
        if t == "main_slideshow" or (stream_from_main and t == "slideshow"):
            m_mode = target.get("mode") if target.get("mode") in ("random", "sequential") else default_mode
            m_int = target.get("interval") or default_interval
            return {
                "type": "website",
                "url": _build_main_viewer_url(main_base_url, mon_id, m_mode, m_int, item_fit)
            }
        if t == "main_image" or (stream_from_main and t == "image"):
            img_name = target.get("image") or target.get("value") or ""
            return {
                "type": "website",
                "url": _build_main_viewer_url(main_base_url, mon_id, single_image=img_name, fit=item_fit) if img_name else ""
            }
        return target

    if "monitor1" in data or "monitor2" in data:
        if "monitor1" in data:
            data["monitor1"] = _transform_target(data["monitor1"], "1")
        if "monitor2" in data:
            data["monitor2"] = _transform_target(data["monitor2"], "2")
        return data

    # Top-level slideshow or single image streamed from Main Pi
    if stream_from_main:
        mon = str(data.get("monitor", "both"))
        mode_val = data.get("mode", "")
        if mode_val == "slideshow" or data.get("slideshow"):
            out = {"monitor": mon}
            if mon in ("1", "both"):
                out["monitor1"] = {
                    "type": "website",
                    "url": _build_main_viewer_url(main_base_url, "1", default_mode, default_interval, default_fit)
                }
            if mon in ("2", "both"):
                out["monitor2"] = {
                    "type": "website",
                    "url": _build_main_viewer_url(main_base_url, "2", default_mode, default_interval, default_fit)
                }
            return out
        elif mode_val == "image" or "image1" in data or "image2" in data:
            out = {"monitor": mon}
            img1 = data.get("image1") or data.get("image2") or ""
            img2 = data.get("image2") or data.get("image1") or ""
            if mon in ("1", "both") and img1:
                out["monitor1"] = {
                    "type": "website",
                    "url": _build_main_viewer_url(main_base_url, "1", single_image=img1, fit=default_fit)
                }
            if mon in ("2", "both") and img2:
                out["monitor2"] = {
                    "type": "website",
                    "url": _build_main_viewer_url(main_base_url, "2", single_image=img2, fit=default_fit)
                }
            return out

    return data


def _prepare_local_display_payload(payload):
    """Normalize 'main_slideshow' / 'main_image' back to native 'slideshow' / 'image' when executing locally."""
    data = dict(payload or {})
    data.pop("stream_from_main", None)

    def _norm(target):
        if not isinstance(target, dict):
            return target
        t = dict(target)
        if t.get("type") == "main_slideshow":
            t["type"] = "slideshow"
        elif t.get("type") == "main_image":
            t["type"] = "image"
        return t

    if "monitor1" in data:
        data["monitor1"] = _norm(data["monitor1"])
    if "monitor2" in data:
        data["monitor2"] = _norm(data["monitor2"])
    return data


def dispatch_to_node(node_id, action="display", payload=None, main_base_url=None, request_host=None):
    """
    Execute a display action ('display', 'blank', 'wake', 'rotate') on 'local' or a remote Pi node.
    Returns (success: bool, message: str, response_data: dict).
    """
    payload = payload or {}
    node = get_node_by_id(node_id)
    if not node:
        return False, f"Pi node '{node_id}' not found", {}

    if node.get("is_local") or is_self_node(node.get("url", ""), request_host=request_host):
        if action == "blank":
            ok, msg = trigger_display_action("blank")
            return ok, msg, {"state": dict(display_state)}
        if action == "wake":
            ok, msg = trigger_display_action("wake")
            return ok, msg, {"state": dict(display_state)}
        if action == "rotate":
            monitor = str(payload.get("monitor", "1"))
            rotation = payload.get("rotation", "normal")
            save_default = bool(payload.get("save_default", False))
            restart_browser = bool(payload.get("restart_browser", True))
            if monitor == "both":
                ok, msg = apply_display_rotations({"1": rotation, "2": rotation}, save_default=save_default, restart_chromium=restart_browser)
            else:
                ok, msg = apply_monitor_rotation(monitor, rotation, save_default=save_default, restart_chromium=restart_browser)
            return ok, msg, {}

        local_data = _prepare_local_display_payload(payload)
        mode = local_data.get("mode", "")
        if mode == "slideshow" or local_data.get("slideshow"):
            ok, msg = trigger_display_action("slideshow", local_data)
        elif "image1" in local_data or "image2" in local_data or mode == "image":
            ok, msg = trigger_display_action("image", local_data)
        else:
            ok, msg = trigger_display_action("website", local_data)
        return ok, msg, {"state": dict(display_state)}

    # Remote Pi node dispatch
    if action == "blank":
        method, path, req_body = "DELETE", "/api/display", None
    elif action == "wake":
        method, path, req_body = "POST", "/api/display/wake", b"{}"
    elif action == "rotate":
        method, path, req_body = "POST", "/api/display/rotate", json.dumps(payload).encode("utf-8")
    else:
        remote_payload = prepare_remote_display_payload(payload, main_base_url or resolve_public_base_url())
        method, path, req_body = "POST", "/api/display", json.dumps(remote_payload).encode("utf-8")

    ok, status_code, resp_bytes, _, err, _ = remote_request(
        node,
        method=method,
        path=path,
        body=req_body,
        content_type="application/json",
        timeout=12.0
    )
    if not ok:
        return False, f"{node.get('name', node_id)}: {err}", {}

    try:
        resp_json = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
    except Exception:
        resp_json = {}

    if 200 <= status_code < 300 and resp_json.get("success", True):
        return True, resp_json.get("message", f"Updated {node.get('name', node_id)}"), resp_json

    err_detail = resp_json.get("error") or err or f"HTTP {status_code}"
    return False, f"{node.get('name', node_id)}: {err_detail}", resp_json


def broadcast_to_nodes(
    action="display",
    payload=None,
    target_node_ids=None,
    include_local=True,
    main_base_url=None,
    request_host=None
):
    """
    Broadcast a display action ('display', 'blank', 'wake') across Main Pi and connected Pis concurrently.
    """
    cfg = load_nodes_config()
    targets = []

    if target_node_ids and isinstance(target_node_ids, list):
        for nid in target_node_ids:
            n = get_node_by_id(nid)
            if n:
                targets.append(n)
    else:
        if include_local:
            local_n = dict(cfg["local"])
            local_n["id"] = "local"
            local_n["is_local"] = True
            targets.append(local_n)
        for n in cfg.get("nodes", []):
            if n.get("enabled", True) and not is_self_node(n.get("url", ""), request_host=request_host):
                targets.append(dict(n))

    if not targets:
        return False, "No active Pi nodes selected for broadcast", []

    resolved_main_url = main_base_url or resolve_public_base_url()
    results = [None] * len(targets)

    def _run_one(node_item):
        nid = node_item.get("id", "local")
        ok, msg, data = dispatch_to_node(
            nid,
            action=action,
            payload=payload,
            main_base_url=resolved_main_url,
            request_host=request_host
        )
        return {
            "id": nid,
            "name": node_item.get("name", nid),
            "url": node_item.get("url", ""),
            "success": ok,
            "message": msg
        }

    with ThreadPoolExecutor(max_workers=min(8, len(targets))) as executor:
        futs = {executor.submit(_run_one, t): i for i, t in enumerate(targets)}
        for fut in as_completed(futs):
            idx = futs[fut]
            try:
                results[idx] = fut.result()
            except Exception as e:
                t = targets[idx]
                results[idx] = {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "url": t.get("url", ""),
                    "success": False,
                    "message": str(e)
                }

    succeeded = sum(1 for r in results if r and r.get("success"))
    total = len(results)
    overall_ok = succeeded > 0
    summary = f"Applied to {succeeded}/{total} Pi node(s)"
    return overall_ok, summary, results


def _encode_multipart_formdata(fields, files):
    """
    Encode fields and file uploads into multipart/form-data bytes without external dependencies.
    fields: dict of {name: value}
    files: list of (field_name, filename, file_bytes, mime_type)
    """
    boundary = f"----PiDisplaySyncBoundary{uuid.uuid4().hex}"
    chunks = []

    for key, val in (fields or {}).items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(f"{val}\r\n".encode("utf-8"))

    for field_name, filename, file_bytes, mime_type in (files or []):
        safe_fn = filename.replace('"', "_")
        ct = mime_type or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{safe_fn}"\r\n'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {ct}\r\n\r\n".encode("utf-8"))
        chunks.append(file_bytes)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def sync_media_to_node(node_id, sync_websites=True, sync_images=False, sync_slideshow=True):
    """
    Synchronize saved websites, slideshow settings, and/or uploaded images from this Pi to a remote Pi.
    """
    node = get_node_by_id(node_id)
    if not node or node.get("is_local"):
        return False, "Valid remote Pi node is required for sync", {}

    summary = {
        "websites_added": 0,
        "images_uploaded": 0,
        "slideshow_synced": False,
        "errors": []
    }

    # 1. Sync Websites
    if sync_websites:
        ok, code, body, _, err, _ = remote_request(node, method="GET", path="/api/websites", timeout=6.0)
        if not ok or code != 200:
            return False, f"Cannot reach {node.get('name')}: {err or f'HTTP {code}'}", summary
        try:
            remote_sites = json.loads(body.decode("utf-8"))
        except Exception:
            remote_sites = []

        existing_keys = {
            ((s.get("name") or "").strip().lower(), (s.get("url") or "").strip().lower())
            for s in remote_sites if isinstance(s, dict)
        }
        existing_urls = {
            (s.get("url") or "").strip().lower()
            for s in remote_sites if isinstance(s, dict) and (s.get("url") or "").strip()
        }

        for site in load_websites():
            s_name = (site.get("name") or "").strip()
            s_url = (site.get("url") or "").strip()
            if not s_name:
                continue
            if (s_name.lower(), s_url.lower()) in existing_keys or (s_url and s_url.lower() in existing_urls):
                continue
            ok_add, add_code, _, _, add_err, _ = remote_request(
                node,
                method="POST",
                path="/api/websites",
                body=json.dumps({"name": s_name, "url": s_url}).encode("utf-8"),
                timeout=6.0
            )
            if ok_add and 200 <= add_code < 300:
                summary["websites_added"] += 1
            else:
                summary["errors"].append(f"Website '{s_name}': {add_err or f'HTTP {add_code}'}")

    # 2. Sync Slideshow Configuration
    if sync_slideshow:
        local_ss = dict(load_slideshow_config())
        # Don't overwrite remote selected_images IDs unless images are identical
        local_ss.pop("selected_images", None)
        ok_ss, ss_code, _, _, ss_err, _ = remote_request(
            node,
            method="POST",
            path="/api/slideshow",
            body=json.dumps(local_ss).encode("utf-8"),
            timeout=6.0
        )
        if ok_ss and 200 <= ss_code < 300:
            summary["slideshow_synced"] = True
        elif not sync_websites:
            return False, f"Failed to sync slideshow settings: {ss_err or f'HTTP {ss_code}'}", summary

    # 3. Sync Uploaded Images
    if sync_images:
        ok_i, i_code, i_body, _, i_err, _ = remote_request(node, method="GET", path="/api/images", timeout=8.0)
        if not ok_i or i_code != 200:
            return False, f"Failed to query images on {node.get('name')}: {i_err or f'HTTP {i_code}'}", summary
        try:
            remote_imgs = json.loads(i_body.decode("utf-8"))
        except Exception:
            remote_imgs = []

        remote_orig_names = {
            (img.get("original_filename") or "").lower()
            for img in remote_imgs if isinstance(img, dict) and img.get("original_filename")
        }
        remote_titles = {
            (img.get("name") or "").strip().lower()
            for img in remote_imgs if isinstance(img, dict) and img.get("name")
        }

        for img in load_images():
            filename = img.get("filename", "")
            orig_name = img.get("original_filename") or filename
            title = img.get("name") or orig_name
            if not filename:
                continue
            if orig_name.lower() in remote_orig_names and title.strip().lower() in remote_titles:
                continue

            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if not os.path.exists(filepath):
                filepath = os.path.join(LEGACY_UPLOADS, filename)
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
            except Exception as e:
                summary["errors"].append(f"Image '{title}': {e}")
                continue

            mime_type, _ = mimetypes.guess_type(orig_name)
            mp_body, mp_ct = _encode_multipart_formdata(
                fields={"name": title},
                files=[("file", orig_name, file_bytes, mime_type or "image/jpeg")]
            )
            ok_up, up_code, _, _, up_err, _ = remote_request(
                node,
                method="POST",
                path="/api/images",
                body=mp_body,
                content_type=mp_ct,
                timeout=20.0
            )
            if ok_up and 200 <= up_code < 300:
                summary["images_uploaded"] += 1
            else:
                summary["errors"].append(f"Image '{title}': {up_err or f'HTTP {up_code}'}")

    parts = []
    if sync_websites:
        parts.append(f"{summary['websites_added']} new website(s)")
    if sync_images:
        parts.append(f"{summary['images_uploaded']} new image(s)")
    if summary["slideshow_synced"]:
        parts.append("slideshow settings")

    msg = f"Synced {', '.join(parts) if parts else 'configuration'} to {node.get('name')}"
    return True, msg, summary

