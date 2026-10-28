"""
Multi-Pi Node Management, Remote Proxy, Broadcast, and Media Sync REST API endpoints.
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, Response

from services.storage import load_nodes_config, save_nodes_config
from services.nodes_service import (
    PROXY_HOP_HEADER,
    normalize_node_url,
    is_self_node,
    get_node_by_id,
    resolve_public_base_url,
    remote_request,
    probe_node,
    get_local_node_overview,
    get_all_nodes_overview,
    dispatch_to_node,
    broadcast_to_nodes,
    sync_media_to_node
)

api_nodes_bp = Blueprint("api_nodes", __name__)


def _is_proxy_loop():
    """Return True if incoming request already traversed a Pi node proxy hop."""
    hop_val = request.headers.get(PROXY_HOP_HEADER, "0")
    try:
        return int(hop_val) >= 1
    except ValueError:
        return True


@api_nodes_bp.route("/api/nodes", methods=["GET"])
def list_nodes():
    """Return configured local and remote Pi nodes immediately (without network probing)."""
    cfg = load_nodes_config()
    local_node = dict(cfg["local"])
    local_node["id"] = "local"
    local_node["is_local"] = True
    local_node["enabled"] = True

    remote_list = []
    for n in cfg.get("nodes", []):
        if is_self_node(n.get("url", ""), request_host=request.host) and not request.args.get("include_self"):
            continue
        item = dict(n)
        item["is_local"] = False
        item["has_api_key"] = bool(item.pop("api_key", ""))
        remote_list.append(item)

    return jsonify({
        "success": True,
        "local": local_node,
        "nodes": remote_list,
        "all_nodes": [local_node] + remote_list,
        "main_base_url": resolve_public_base_url(request.host_url)
    })


@api_nodes_bp.route("/api/nodes/overview", methods=["GET"])
def nodes_overview():
    """Poll live status, display state, and connected monitors across all configured Pis concurrently."""
    overview = get_all_nodes_overview(request_host=request.host)
    online_count = sum(1 for n in overview if n.get("online"))
    total_displays = sum(int(n.get("monitor_count") or 0) for n in overview if n.get("online"))
    return jsonify({
        "success": True,
        "nodes": overview,
        "summary": {
            "total_nodes": len(overview),
            "online_nodes": online_count,
            "total_displays": total_displays
        }
    })


@api_nodes_bp.route("/api/nodes/probe", methods=["POST"])
def probe_node_route():
    """Test connectivity to a candidate Pi Display Control URL and discover its displays."""
    data = request.json or {}
    raw_url = (data.get("url") or "").strip()
    verify_ssl = bool(data.get("verify_ssl", True))
    api_key = (data.get("api_key") or "").strip()
    auto_discover = bool(data.get("auto_discover", True))

    if not raw_url:
        return jsonify({"success": False, "error": "Pi hostname or URL is required"}), 400

    try:
        result = probe_node(
            raw_url,
            verify_ssl=verify_ssl,
            api_key=api_key,
            auto_discover=auto_discover
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    return jsonify({
        "success": True,
        "probe": result
    })


@api_nodes_bp.route("/api/nodes", methods=["POST"])
def add_node():
    """Connect and persist a new remote Pi running Pi Display Control."""
    data = request.json or {}
    name = (data.get("name") or "").strip()
    raw_url = (data.get("url") or "").strip()
    role = (data.get("role") or "secondary").strip() or "secondary"
    verify_ssl = bool(data.get("verify_ssl", True))
    api_key = (data.get("api_key") or "").strip()
    auto_discover = bool(data.get("auto_discover", False))

    if not name:
        return jsonify({"success": False, "error": "Pi name is required"}), 400
    if not raw_url:
        return jsonify({"success": False, "error": "Pi hostname or URL is required"}), 400

    try:
        clean_url = normalize_node_url(raw_url)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    probe_res = None
    if auto_discover:
        probe_res = probe_node(raw_url, verify_ssl=verify_ssl, api_key=api_key, auto_discover=True)
        if probe_res.get("online") and probe_res.get("resolved_url"):
            clean_url = probe_res["resolved_url"]

    cfg = load_nodes_config()
    for existing in cfg.get("nodes", []):
        try:
            if normalize_node_url(existing.get("url", "")).lower() == clean_url.lower():
                return jsonify({
                    "success": False,
                    "error": f"A connected Pi at {clean_url} already exists ({existing.get('name')})"
                }), 400
        except ValueError:
            pass

    new_node = {
        "id": f"pi-{uuid.uuid4().hex[:8]}",
        "name": name,
        "url": clean_url,
        "role": role,
        "enabled": True,
        "verify_ssl": verify_ssl,
        "api_key": api_key,
        "created_at": datetime.now().isoformat()
    }
    cfg.setdefault("nodes", []).append(new_node)
    save_nodes_config(cfg)

    safe_node = dict(new_node)
    safe_node["is_local"] = False
    safe_node["has_api_key"] = bool(safe_node.pop("api_key", ""))

    return jsonify({
        "success": True,
        "message": f"Connected {name} ({clean_url})",
        "node": safe_node,
        "probe": probe_res
    })


@api_nodes_bp.route("/api/nodes/<node_id>", methods=["PUT"])
def update_node(node_id):
    """Update local Pi metadata (name / public URL) or a connected remote Pi configuration."""
    data = request.json or {}
    cfg = load_nodes_config()

    if node_id == "local":
        local_cfg = cfg["local"]
        if "name" in data and str(data["name"]).strip():
            local_cfg["name"] = str(data["name"]).strip()
        if "url" in data and str(data["url"]).strip():
            try:
                local_cfg["url"] = normalize_node_url(str(data["url"]))
            except ValueError as e:
                return jsonify({"success": False, "error": str(e)}), 400
        if "role" in data and str(data["role"]).strip():
            local_cfg["role"] = str(data["role"]).strip()
        save_nodes_config(cfg)
        out = dict(local_cfg)
        out["is_local"] = True
        return jsonify({"success": True, "message": "Updated local Pi settings", "node": out})

    target = None
    for n in cfg.get("nodes", []):
        if n.get("id") == node_id:
            target = n
            break

    if not target:
        return jsonify({"success": False, "error": "Pi node not found"}), 404

    if "name" in data and str(data["name"]).strip():
        target["name"] = str(data["name"]).strip()
    if "url" in data and str(data["url"]).strip():
        try:
            target["url"] = normalize_node_url(str(data["url"]))
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
    if "role" in data and str(data["role"]).strip():
        target["role"] = str(data["role"]).strip()
    if "enabled" in data:
        target["enabled"] = bool(data["enabled"])
    if "verify_ssl" in data:
        target["verify_ssl"] = bool(data["verify_ssl"])
    if "api_key" in data and data["api_key"] is not None:
        target["api_key"] = str(data["api_key"]).strip()

    save_nodes_config(cfg)
    safe_node = dict(target)
    safe_node["is_local"] = False
    safe_node["has_api_key"] = bool(safe_node.pop("api_key", ""))
    return jsonify({"success": True, "message": f"Updated {target['name']}", "node": safe_node})


@api_nodes_bp.route("/api/nodes/<node_id>", methods=["DELETE"])
def delete_node(node_id):
    """Disconnect and remove a remote Pi node."""
    if node_id == "local":
        return jsonify({"success": False, "error": "Cannot remove the local Pi node"}), 400

    cfg = load_nodes_config()
    before = len(cfg.get("nodes", []))
    cfg["nodes"] = [n for n in cfg.get("nodes", []) if n.get("id") != node_id]
    if len(cfg["nodes"]) == before:
        return jsonify({"success": False, "error": "Pi node not found"}), 404

    save_nodes_config(cfg)
    return jsonify({"success": True, "message": "Disconnected Pi node"})


@api_nodes_bp.route("/api/nodes/<node_id>/status", methods=["GET"])
def single_node_status(node_id):
    """Fetch live status and connected monitors for a single Pi node."""
    if node_id == "local":
        return jsonify({"success": True, "node": get_local_node_overview()})

    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"success": False, "error": "Pi node not found"}), 404

    probe_res = probe_node(
        node.get("url", ""),
        verify_ssl=bool(node.get("verify_ssl", True)),
        api_key=node.get("api_key", ""),
        auto_discover=False
    )
    out = dict(node)
    out.pop("api_key", None)
    out.update(probe_res)
    return jsonify({"success": True, "node": out})


@api_nodes_bp.route("/api/nodes/<node_id>/display", methods=["POST"])
def node_display_action(node_id):
    """
    Dispatch a display action ('display', 'blank', 'wake', 'rotate') to a specific Pi node.
    Supports streaming Main Pi's slideshow/images to remote Pis via stream_from_main=True.
    """
    if _is_proxy_loop():
        return jsonify({"success": False, "error": "Proxy loop prevented"}), 400

    data = request.json or {}
    action = data.get("action", "display")
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
    main_base = resolve_public_base_url(request.host_url)

    ok, msg, resp_data = dispatch_to_node(
        node_id,
        action=action,
        payload=payload,
        main_base_url=main_base,
        request_host=request.host
    )
    status_code = 200 if ok else 502
    return jsonify({
        "success": ok,
        "message": msg if ok else None,
        "error": None if ok else msg,
        "data": resp_data
    }), status_code


@api_nodes_bp.route("/api/nodes/broadcast", methods=["POST"])
def broadcast_route():
    """
    Broadcast a display update, slideshow, image, wake, or blank command across all connected Pis.
    """
    if _is_proxy_loop():
        return jsonify({"success": False, "error": "Proxy loop prevented"}), 400

    data = request.json or {}
    action = data.get("action", "display")
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
    target_node_ids = data.get("node_ids")
    include_local = bool(data.get("include_local", True))
    main_base = resolve_public_base_url(request.host_url)

    ok, summary, results = broadcast_to_nodes(
        action=action,
        payload=payload,
        target_node_ids=target_node_ids,
        include_local=include_local,
        main_base_url=main_base,
        request_host=request.host
    )
    return jsonify({
        "success": ok,
        "message": summary,
        "error": None if ok else summary,
        "results": results
    }), (200 if ok else 502)


@api_nodes_bp.route("/api/nodes/<node_id>/sync", methods=["POST"])
def sync_node_route(node_id):
    """Synchronize saved websites, slideshow config, and/or images to a connected remote Pi."""
    if _is_proxy_loop():
        return jsonify({"success": False, "error": "Proxy loop prevented"}), 400

    data = request.json or {}
    sync_websites = bool(data.get("websites", True))
    sync_images = bool(data.get("images", False))
    sync_slideshow = bool(data.get("slideshow", True))

    ok, msg, summary = sync_media_to_node(
        node_id,
        sync_websites=sync_websites,
        sync_images=sync_images,
        sync_slideshow=sync_slideshow
    )
    return jsonify({
        "success": ok,
        "message": msg if ok else None,
        "error": None if ok else msg,
        "summary": summary
    }), (200 if ok else 502)


@api_nodes_bp.route("/api/nodes/<node_id>/proxy/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_node_api(node_id, subpath):
    """
    Transparent server-to-server proxy to a connected Pi's /api/* endpoints.
    Eliminates browser CORS / mixed-content issues and supports binary images & multipart uploads.
    """
    if _is_proxy_loop():
        return jsonify({"success": False, "error": "Proxy loop prevented"}), 400

    clean_sub = subpath.lstrip("/")
    if not clean_sub.startswith("api/") or clean_sub.startswith("api/nodes"):
        return jsonify({"success": False, "error": "Invalid proxied API path"}), 400

    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"success": False, "error": f"Pi node '{node_id}' not found"}), 404

    if node.get("is_local") or is_self_node(node.get("url", ""), request_host=request.host):
        return jsonify({"success": False, "error": "Target node resolves to this local Pi; use direct local API"}), 400

    raw_body = request.get_data(cache=False) if request.method in ("POST", "PUT", "DELETE") else None
    req_ct = request.headers.get("Content-Type", "application/json")
    timeout = 20.0 if (request.method == "POST" and clean_sub == "api/images") else 10.0

    # Special handling when proxying POST /api/display with main_slideshow / main_image targets
    if request.method == "POST" and clean_sub == "api/display" and raw_body and "application/json" in req_ct:
        try:
            import json as _json
            from services.nodes_service import prepare_remote_display_payload
            parsed_body = _json.loads(raw_body.decode("utf-8"))
            transformed = prepare_remote_display_payload(parsed_body, resolve_public_base_url(request.host_url))
            raw_body = _json.dumps(transformed).encode("utf-8")
        except Exception:
            pass

    ok, status_code, resp_bytes, resp_ct, err, _ = remote_request(
        node,
        method=request.method,
        path=f"/{clean_sub}",
        query_string=request.query_string,
        body=raw_body if raw_body else None,
        content_type=req_ct if raw_body else None,
        timeout=timeout
    )

    if not ok:
        return jsonify({
            "success": False,
            "error": f"Could not reach {node.get('name', node_id)} ({node.get('url')}): {err}"
        }), 502

    return Response(resp_bytes, status=status_code, content_type=resp_ct)

