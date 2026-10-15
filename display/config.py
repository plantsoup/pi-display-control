"""
Display hardware configuration and default orientation persistence.
Stores monitor defaults (such as startup rotations) across reboots and restarts.
"""

import os
import sys
import json
import threading

# Default rotation settings matching existing hardware setup (m1=left, m2=right)
DEFAULT_DISPLAY_CONFIG = {
    "monitors": {
        "1": {
            "rotation": "left"
        },
        "2": {
            "rotation": "right"
        }
    }
}

VALID_ROTATIONS = ["normal", "left", "right", "inverted"]

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
                            data["monitors"] = DEFAULT_DISPLAY_CONFIG["monitors"].copy()
                        for m_id in ["1", "2"]:
                            if m_id not in data["monitors"] or not isinstance(data["monitors"][m_id], dict):
                                data["monitors"][m_id] = DEFAULT_DISPLAY_CONFIG["monitors"][m_id].copy()
                            elif "rotation" not in data["monitors"][m_id] or data["monitors"][m_id]["rotation"] not in VALID_ROTATIONS:
                                data["monitors"][m_id]["rotation"] = DEFAULT_DISPLAY_CONFIG["monitors"][m_id]["rotation"]
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
        return DEFAULT_DISPLAY_CONFIG.copy()

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
