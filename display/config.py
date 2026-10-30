"""
Display hardware configuration, startup orientation, and default site/wallpaper persistence.
Stores monitor defaults (startup rotations, default site/wallpaper) across reboots and restarts.
"""

import os
import sys
import json
import threading

DEFAULT_AUTODARTS_URL = os.getenv("DEFAULT_DISPLAY_URL", os.getenv("AUTODARTS_URL", "https://play.autodarts.io"))
DEFAULT_AUTODARTS_URL2 = os.getenv("DEFAULT_DISPLAY_URL2", os.getenv("AUTODARTS_URL2", DEFAULT_AUTODARTS_URL))

# Default rotation and content settings matching existing hardware setup (m1=left/autodarts, m2=right/slideshow)
DEFAULT_DISPLAY_CONFIG = {
    "monitors": {
        "1": {
            "rotation": "left",
            "default_content": {
                "type": "website",
                "url": "",
                "name": "Autodarts Board"
            }
        },
        "2": {
            "rotation": "right",
            "default_content": {
                "type": "slideshow",
                "mode": "random",
                "interval": 30,
                "fit": "cover"
            }
        }
    }
}

VALID_ROTATIONS = ["normal", "left", "right", "inverted"]
VALID_CONTENT_TYPES = ["website", "image", "slideshow"]

ROTATION_METADATA = [
    {
        "value": "normal",
        "label": "Landscape (Normal / 0°)",
        "angle": 0,
        "orientation": "landscape"
    },
    {
        "value": "left",
        "label": "Portrait (Left / 270° CCW)",
        "angle": 270,
        "orientation": "portrait"
    },
    {
        "value": "right",
        "label": "Portrait (Right / 90° CW)",
        "angle": 90,
        "orientation": "portrait"
    },
    {
        "value": "inverted",
        "label": "Inverted Landscape (180°)",
        "angle": 180,
        "orientation": "landscape"
    }
]

_config_lock = threading.Lock()

def normalize_default_content(content, monitor_id="1"):
    """Normalize and validate a monitor default content dictionary (site or wallpaper)"""
    if not isinstance(content, dict):
        if isinstance(content, str) and content.strip():
            raw_str = content.strip()
            if raw_str.startswith("http://") or raw_str.startswith("https://"):
                content = {"type": "website", "url": raw_str, "name": raw_str}
            elif any(raw_str.lower().endswith("." + ext) for ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"]):
                content = {"type": "image", "image": raw_str, "fit": "cover"}
            elif raw_str == "slideshow":
                content = {"type": "slideshow", "mode": "random", "interval": 30, "fit": "cover"}
            else:
                content = {"type": "website", "url": raw_str}
        else:
            content = {}

    ctype = content.get("type", "website")
    if ctype not in VALID_CONTENT_TYPES:
        ctype = "website"

    if ctype == "website":
        raw_url = str(content.get("url", "") or "").strip()
        raw_name = str(content.get("name", "") or "").strip()
        if not raw_name:
            raw_name = "Autodarts Board" if not raw_url else raw_url
        return {
            "type": "website",
            "url": raw_url,
            "name": raw_name
        }
    elif ctype == "image":
        raw_image = str(content.get("image", "") or content.get("value", "") or "").strip()
        raw_name = str(content.get("name", "") or "").strip() or raw_image or "Wallpaper Image"
        fit = content.get("fit", "cover")
        if fit not in ["cover", "contain"]:
            fit = "cover"
        return {
            "type": "image",
            "image": raw_image,
            "name": raw_name,
            "fit": fit
        }
    elif ctype == "slideshow":
        mode = content.get("mode", "random")
        if mode not in ["random", "sequential"]:
            mode = "random"
        try:
            interval = max(2, int(content.get("interval", 30)))
        except (ValueError, TypeError):
            interval = 30
        fit = content.get("fit", "cover")
        if fit not in ["cover", "contain"]:
            fit = "cover"
        return {
            "type": "slideshow",
            "mode": mode,
            "interval": interval,
            "fit": fit,
            "name": str(content.get("name", "") or "").strip() or f"Slideshow ({mode}, {interval}s)"
        }

def get_display_config_path():
    """Resolve display settings JSON path from environment or project data directory"""
    custom = os.getenv('DISPLAY_CONFIG_FILE')
    if custom:
        return custom
    data_dir = os.getenv('DATA_DIR')
    if not data_dir:
        if os.path.exists('/data') and os.access('/data', os.W_OK):
            data_dir = '/data'
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(app_dir, 'data')
    return os.path.join(data_dir, "display_settings.json")

def load_display_config():
    """Load display settings from JSON file with safe fallback to defaults"""
    filepath = get_display_config_path()
    with _config_lock:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Ensure monitors structure exists
                        if "monitors" not in data or not isinstance(data["monitors"], dict):
                            data["monitors"] = {
                                "1": DEFAULT_DISPLAY_CONFIG["monitors"]["1"].copy(),
                                "2": DEFAULT_DISPLAY_CONFIG["monitors"]["2"].copy()
                            }
                        for m_id in ["1", "2"]:
                            if m_id not in data["monitors"] or not isinstance(data["monitors"][m_id], dict):
                                data["monitors"][m_id] = DEFAULT_DISPLAY_CONFIG["monitors"][m_id].copy()
                            else:
                                if "rotation" not in data["monitors"][m_id] or data["monitors"][m_id]["rotation"] not in VALID_ROTATIONS:
                                    data["monitors"][m_id]["rotation"] = DEFAULT_DISPLAY_CONFIG["monitors"][m_id]["rotation"]
                                if "default_content" not in data["monitors"][m_id]:
                                    data["monitors"][m_id]["default_content"] = DEFAULT_DISPLAY_CONFIG["monitors"][m_id]["default_content"].copy()
                                else:
                                    data["monitors"][m_id]["default_content"] = normalize_default_content(
                                        data["monitors"][m_id]["default_content"], monitor_id=m_id
                                    )
                        return data
            except Exception as e:
                print(f"[WARN] Error loading display config from {filepath}: {e}", file=sys.stderr)
        
        # Save and return default config if missing or corrupted
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_DISPLAY_CONFIG, f, indent=2)
        except Exception:
            pass
        return {
            "monitors": {
                "1": {
                    "rotation": DEFAULT_DISPLAY_CONFIG["monitors"]["1"]["rotation"],
                    "default_content": DEFAULT_DISPLAY_CONFIG["monitors"]["1"]["default_content"].copy()
                },
                "2": {
                    "rotation": DEFAULT_DISPLAY_CONFIG["monitors"]["2"]["rotation"],
                    "default_content": DEFAULT_DISPLAY_CONFIG["monitors"]["2"]["default_content"].copy()
                }
            }
        }

def save_display_config(config):
    """Save display settings to JSON file atomically"""
    filepath = get_display_config_path()
    with _config_lock:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            temp_path = f"{filepath}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            os.replace(temp_path, filepath)
            return True
        except Exception as e:
            print(f"[ERROR] Saving display config to {filepath}: {e}", file=sys.stderr)
            return False

def get_monitor_rotation(monitor_id="1", default=None):
    """Get the persistent default rotation for a monitor ('1' or '2')"""
    cfg = load_display_config()
    mon_key = str(monitor_id)
    fallback = default if default in VALID_ROTATIONS else ("left" if mon_key == "1" else "right")
    mon_info = cfg.get("monitors", {}).get(mon_key, {})
    return mon_info.get("rotation", fallback)

def set_default_rotation(monitor_id, rotation):
    """Save persistent default rotation for a monitor ('1' or '2')"""
    if rotation not in VALID_ROTATIONS:
        raise ValueError(f"Invalid rotation '{rotation}'. Valid choices: {VALID_ROTATIONS}")
    cfg = load_display_config()
    mon_key = str(monitor_id)
    if "monitors" not in cfg:
        cfg["monitors"] = {}
    if mon_key not in cfg["monitors"]:
        cfg["monitors"][mon_key] = {}
    cfg["monitors"][mon_key]["rotation"] = rotation
    save_display_config(cfg)
    return True

def get_monitor_default_content(monitor_id="1"):
    """Get persistent default site/wallpaper for a monitor ('1' or '2')"""
    cfg = load_display_config()
    mon_key = str(monitor_id)
    fallback = DEFAULT_DISPLAY_CONFIG["monitors"].get(mon_key, DEFAULT_DISPLAY_CONFIG["monitors"]["1"])["default_content"]
    mon_info = cfg.get("monitors", {}).get(mon_key, {})
    raw = mon_info.get("default_content", fallback)
    return normalize_default_content(raw, monitor_id=mon_key)

def set_monitor_default_content(monitor_id, content):
    """Save persistent default site or wallpaper for a monitor ('1' or '2')"""
    mon_key = str(monitor_id)
    if mon_key not in ["1", "2"]:
        raise ValueError(f"Invalid monitor_id '{monitor_id}'. Must be '1' or '2'")
    normalized = normalize_default_content(content, monitor_id=mon_key)
    cfg = load_display_config()
    if "monitors" not in cfg:
        cfg["monitors"] = {}
    if mon_key not in cfg["monitors"]:
        cfg["monitors"][mon_key] = {}
    cfg["monitors"][mon_key]["default_content"] = normalized
    save_display_config(cfg)
    return True

def resolve_monitor_default_url(monitor_id="1"):
    """Resolve the kiosk URL for a monitor's configured default site/wallpaper"""
    content = get_monitor_default_content(monitor_id)
    ctype = content.get("type", "website")
    mon_key = str(monitor_id)
    port = int(os.getenv("PORT", 5000))

    if ctype == "image":
        img = content.get("image", "").strip()
        if img:
            fit = content.get("fit", "cover")
            return f"http://127.0.0.1:{port}/viewer?single={img}&monitor={mon_key}&fit={fit}"
        # Fallback to autodarts default if no image filename set
        return DEFAULT_AUTODARTS_URL if mon_key == "1" else DEFAULT_AUTODARTS_URL2

    elif ctype == "slideshow":
        mode = content.get("mode", "random")
        interval = content.get("interval", 30)
        fit = content.get("fit", "cover")
        return f"http://127.0.0.1:{port}/viewer?monitor={mon_key}&mode={mode}&interval={interval}&fit={fit}"

    else:
        # Website
        url = content.get("url", "").strip()
        if url:
            return url
        return DEFAULT_AUTODARTS_URL if mon_key == "1" else DEFAULT_AUTODARTS_URL2
