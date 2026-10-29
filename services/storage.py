"""
Storage and persistence service.
Handles JSON file operations, uploads directory configuration, and thread-safe CRUD helpers.
"""

import os
import sys
import json
import copy
import socket
import threading
from pathlib import Path

# Directory setup
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration with environment variable overrides
HOME_DIR = os.getenv('WORK_DIR', os.path.expanduser("~"))
PORT = int(os.getenv('PORT', 5000))

# Persistent data paths with safe write-permission fallback
def _get_writable_data_dir():
    custom_data = os.getenv('DATA_DIR')
    if custom_data:
        return custom_data
    # If /data exists and is writable (e.g., inside Docker container)
    if os.path.exists('/data') and os.access('/data', os.W_OK):
        return '/data'
    # Default to local data directory inside project
    return os.path.join(APP_DIR, 'data')

DATA_DIR = _get_writable_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE = os.getenv('CONFIG_FILE', os.path.join(DATA_DIR, "websites.json"))
IMAGES_CONFIG_FILE = os.getenv('IMAGES_CONFIG_FILE', os.path.join(DATA_DIR, "images.json"))
SLIDESHOW_CONFIG_FILE = os.getenv('SLIDESHOW_CONFIG_FILE', os.path.join(DATA_DIR, "slideshow.json"))
SCHEDULES_CONFIG_FILE = os.getenv('SCHEDULES_CONFIG_FILE', os.path.join(DATA_DIR, "schedules.json"))
DISPLAY_CONFIG_FILE = os.getenv('DISPLAY_CONFIG_FILE', os.path.join(DATA_DIR, "display_settings.json"))
NODES_CONFIG_FILE = os.getenv('NODES_CONFIG_FILE', os.path.join(DATA_DIR, "nodes.json"))
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(DATA_DIR, "uploads", "images"))

DEFAULT_MAIN_PI_URL = os.getenv('MAIN_PI_URL', '').strip()
DEFAULT_SECONDARY_PI_URL = os.getenv('SECONDARY_PI_URL', '').strip()

# Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Also check root-level legacy files for backwards compatibility
LEGACY_CONFIG = os.path.join(APP_DIR, "websites.json")
LEGACY_IMAGES = os.path.join(APP_DIR, "images.json")
LEGACY_UPLOADS = os.path.join(APP_DIR, "uploads", "images")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}

# Thread-safe lock for file operations
file_lock = threading.Lock()

def _read_json(filepath, default_value, legacy_fallback=None):
    with file_lock:
        target = filepath
        if not os.path.exists(target) and legacy_fallback and os.path.exists(legacy_fallback):
            target = legacy_fallback
        if os.path.exists(target):
            try:
                with open(target, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Reading {target}: {e}", file=sys.stderr)
        return default_value

def _write_json(filepath, data):
    with file_lock:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Writing {filepath}: {e}", file=sys.stderr)
            return False

def load_websites():
    default_websites = [
        {"id": "default-autodarts", "name": "Autodarts Board", "url": "", "is_default": True},
        {"id": "default-8bit", "name": "8-bit Website", "url": "https://8bit.website.com", "is_default": False}
    ]
    data = _read_json(CONFIG_FILE, None, LEGACY_CONFIG)
    if data is None:
        save_websites(default_websites)
        return default_websites
    return data

def save_websites(websites):
    _write_json(CONFIG_FILE, websites)

def load_images():
    data = _read_json(IMAGES_CONFIG_FILE, [], LEGACY_IMAGES)
    return data

def save_images(images):
    _write_json(IMAGES_CONFIG_FILE, images)

def load_slideshow_config():
    default_config = {
        "mode": "random",        # "random" (shuffle) or "sequential"
        "interval": 30,          # seconds
        "transition": "fade",    # "fade", "slide", "instant"
        "fit": "cover",          # "cover" (default) or "contain"
        "selected_images": [],   # empty array = all uploaded images
        "background_color": "#000000"
    }
    return _read_json(SLIDESHOW_CONFIG_FILE, default_config)

def save_slideshow_config(config):
    _write_json(SLIDESHOW_CONFIG_FILE, config)

def load_schedules():
    return _read_json(SCHEDULES_CONFIG_FILE, [])

def save_schedules(schedules):
    _write_json(SCHEDULES_CONFIG_FILE, schedules)

def get_default_nodes_config():
    """
    Build default connected Pi nodes configuration.
    Defaults to a single local Main Pi with an auto-detected host URL and no pre-seeded
    remote peers unless MAIN_PI_URL / SECONDARY_PI_URL environment variables are set.
    Automatically inverts local role if running on a host named pi2 / PI_NODE_ROLE=secondary.
    """
    role_env = os.getenv('PI_NODE_ROLE', '').strip().lower()
    main_url = os.getenv('MAIN_PI_URL', DEFAULT_MAIN_PI_URL).strip()
    secondary_url = os.getenv('SECONDARY_PI_URL', DEFAULT_SECONDARY_PI_URL).strip()

    try:
        hostname = socket.gethostname().lower()
    except Exception:
        hostname = ''

    is_secondary_host = (
        role_env == 'secondary'
        or hostname == 'pi2'
        or hostname.startswith('pi2.')
        or hostname.startswith('pi2-')
    )

    if is_secondary_host:
        nodes = []
        if main_url:
            nodes.append({
                "id": "main-pi",
                "name": "Main Pi",
                "url": main_url,
                "role": "main",
                "enabled": True,
                "verify_ssl": True,
                "api_key": ""
            })
        return {
            "local": {
                "id": "local",
                "name": "Secondary Pi",
                "url": secondary_url,
                "role": "secondary"
            },
            "nodes": nodes
        }

    nodes = []
    if secondary_url:
        nodes.append({
            "id": "secondary-pi2",
            "name": "Secondary Pi",
            "url": secondary_url,
            "role": "secondary",
            "enabled": True,
            "verify_ssl": True,
            "api_key": ""
        })

    return {
        "local": {
            "id": "local",
            "name": "Main Pi",
            "url": main_url,
            "role": "main"
        },
        "nodes": nodes
    }

def load_nodes_config():
    default_cfg = get_default_nodes_config()
    data = _read_json(NODES_CONFIG_FILE, None)
    if not isinstance(data, dict):
        return copy.deepcopy(default_cfg)

    local_cfg = data.get("local")
    if not isinstance(local_cfg, dict):
        local_cfg = copy.deepcopy(default_cfg["local"])
    else:
        local_cfg = {
            "id": "local",
            "name": local_cfg.get("name") or default_cfg["local"]["name"],
            "url": local_cfg.get("url") if local_cfg.get("url") is not None else default_cfg["local"]["url"],
            "role": local_cfg.get("role") or default_cfg["local"]["role"]
        }

    nodes_list = data.get("nodes")
    if not isinstance(nodes_list, list):
        nodes_list = copy.deepcopy(default_cfg["nodes"])

    return {
        "local": local_cfg,
        "nodes": copy.deepcopy(nodes_list)
    }

def save_nodes_config(config):
    return _write_json(NODES_CONFIG_FILE, config)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from display.config import (
    load_display_config,
    save_display_config,
    get_monitor_rotation,
    set_default_rotation,
    VALID_ROTATIONS,
    ROTATION_METADATA
)
