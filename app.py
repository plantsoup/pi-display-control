#!/usr/bin/env python3
"""
Raspberry Pi Display Control Interface
Web-based control panel for managing display scripts, websites, 
image slideshows with randomization, and automated time-based schedules.
"""

import os
import sys
import glob

# Auto-detect and include local virtual environment if present
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
for _venv_name in ['.venv', 'venv', 'env']:
    _site_pkgs = glob.glob(os.path.join(_APP_DIR, _venv_name, 'lib', 'python*', 'site-packages'))
    for _p in _site_pkgs:
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)

try:
    from flask import Flask
except ImportError:
    print("[ERROR] Flask is not installed.", file=sys.stderr)
    print("Please install requirements using:", file=sys.stderr)
    print("    pip3 install -r requirements.txt", file=sys.stderr)
    print("or run with the virtual environment:", file=sys.stderr)
    print("    source .venv/bin/activate && python3 app.py", file=sys.stderr)
    sys.exit(1)

import display_manager
from routes import register_routes
from services.storage import (
    APP_DIR,
    HOME_DIR,
    PORT,
    DATA_DIR,
    CONFIG_FILE,
    IMAGES_CONFIG_FILE,
    SLIDESHOW_CONFIG_FILE,
    SCHEDULES_CONFIG_FILE,
    UPLOAD_FOLDER,
    LEGACY_CONFIG,
    LEGACY_IMAGES,
    LEGACY_UPLOADS,
    ALLOWED_EXTENSIONS,
    file_lock,
    load_websites,
    save_websites,
    load_images,
    save_images,
    load_slideshow_config,
    save_slideshow_config,
    load_schedules,
    save_schedules,
    allowed_file
)
from services.display_service import (
    display_state,
    get_viewer_url,
    _resolve_target,
    trigger_display_action
)
from services.scheduler import (
    scheduler_worker,
    start_scheduler_thread
)

def create_app():
    """Application factory for Pi Display Control"""
    flask_app = Flask(__name__)
    register_routes(flask_app)
    return flask_app

app = create_app()

# Start background scheduler thread
start_scheduler_thread()

# ----------------------------------------------------------------------
# Application Entry Point
# ----------------------------------------------------------------------

if __name__ == '__main__':
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    print(f"🚀 Starting Pi Display Control Server on port {PORT}...")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"🖼️ Uploads directory: {UPLOAD_FOLDER}")
    print(f"⚙️ Display Engine: Python display_manager")
    app.run(host='0.0.0.0', port=PORT, debug=debug)
