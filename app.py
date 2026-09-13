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
    from flask import Flask, render_template, request, jsonify, send_from_directory
    from werkzeug.utils import secure_filename
except ImportError:
    print("[ERROR] Flask is not installed.", file=sys.stderr)
    print("Please install requirements using:", file=sys.stderr)
    print("    pip3 install -r requirements.txt", file=sys.stderr)
    print("or run with the virtual environment:", file=sys.stderr)
    print("    source .venv/bin/activate && python3 app.py", file=sys.stderr)
    sys.exit(1)

import subprocess
import json
import uuid
import time
import threading
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Directory setup
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration with environment variable overrides
HOME_DIR = os.getenv('WORK_DIR', os.path.expanduser("~"))
SCRIPT_PATH = os.getenv('SCRIPT_PATH', os.path.join(APP_DIR, "start.sh"))
BLANK_SCREEN_PATH = os.getenv('BLANK_SCREEN_PATH', os.path.join(APP_DIR, "blank-screen.sh"))
WAKE_SCREEN_PATH = os.getenv('WAKE_SCREEN_PATH', os.path.join(APP_DIR, "wake-screen.sh"))
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
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(DATA_DIR, "uploads", "images"))

# Ensure uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Also check root-level legacy files for backwards compatibility
LEGACY_CONFIG = os.path.join(APP_DIR, "websites.json")
LEGACY_IMAGES = os.path.join(APP_DIR, "images.json")
LEGACY_UPLOADS = os.path.join(APP_DIR, "uploads", "images")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}

# Thread-safe lock for file operations
file_lock = threading.Lock()

# Global runtime state tracker
display_state = {
    "status": "idle", # "running", "blank", "idle"
    "mode": "default", # "website", "image", "slideshow", "default"
    "monitor": "both",
    "updated_at": datetime.now().isoformat(),
    "last_message": "Ready"
}

# ----------------------------------------------------------------------
# JSON Storage Helper Functions
# ----------------------------------------------------------------------

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
    # Check if images exist on disk, filter out missing if needed or keep metadata
    return data

def save_images(images):
    _write_json(IMAGES_CONFIG_FILE, images)

def load_slideshow_config():
    default_config = {
        "mode": "random",        # "random" (shuffle) or "sequential"
        "interval": 30,          # seconds
        "transition": "fade",    # "fade", "slide", "instant"
        "fit": "contain",        # "contain", "cover"
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------------------------
# Display Script Execution Helpers
# ----------------------------------------------------------------------

def execute_display_command(cmd, log_name="display"):
    """Execute shell command in background"""
    if not os.path.exists(cmd[0]):
        return False, f"Script not found at {cmd[0]}"
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=APP_DIR
        )
        return True, process.pid
    except Exception as e:
        return False, str(e)

def get_viewer_url(monitor='both', mode='random', interval=30):
    """Generate the local slideshow viewer URL for kiosk display"""
    return f"http://127.0.0.1:{PORT}/viewer?monitor={monitor}&mode={mode}&interval={interval}"

def _resolve_target(item, monitor_id='1', default_params=None):
    """Resolve display target (website, single image, slideshow, default) to a URL"""
    default_params = default_params or {}
    if isinstance(item, dict):
        t = item.get('type', 'website')
        if t == 'website':
            return item.get('url', item.get('value', '')) or ''
        elif t == 'image':
            img = item.get('image', item.get('value', ''))
            return f"http://127.0.0.1:{PORT}/viewer?single={img}" if img else ""
        elif t == 'slideshow':
            mode = item.get('mode', default_params.get('mode', 'random'))
            interval = item.get('interval', default_params.get('interval', 30))
            return get_viewer_url(monitor_id, mode, interval)
        elif t == 'default':
            return ""
        return item.get('value', '')

    if not item:
        return ""
    if item == 'slideshow':
        mode = default_params.get('mode', 'random')
        interval = default_params.get('interval', 30)
        return get_viewer_url(monitor_id, mode, interval)
    if item.startswith('http://') or item.startswith('https://') or item.startswith('file://'):
        return item
    if any(item.lower().endswith('.' + ext) for ext in ALLOWED_EXTENSIONS):
        return f"http://127.0.0.1:{PORT}/viewer?single={item}"
    return item

def trigger_display_action(action_type, params=None):
    """Unified internal handler for triggering display state changes with dual-monitor mixing"""
    params = params or {}
    global display_state

    if action_type == "blank":
        success, res = execute_display_command([BLANK_SCREEN_PATH])
        if success:
            display_state.update({
                "status": "blank",
                "mode": "blank",
                "updated_at": datetime.now().isoformat(),
                "last_message": "Display blanked (screen turned off)"
            })
            return True, "Display blanked successfully"
        return False, f"Failed to blank display: {res}"

    elif action_type == "wake":
        success, res = execute_display_command([WAKE_SCREEN_PATH])
        if success:
            display_state.update({
                "status": "running",
                "mode": "default",
                "updated_at": datetime.now().isoformat(),
                "last_message": "Display woken up"
            })
            return True, "Display woken successfully"
        return False, f"Failed to wake display: {res}"

    # Handle display routing (website, image, slideshow, dual mix)
    monitor = params.get('monitor', 'both')
    
    # Save slideshow config if options provided
    if action_type == 'slideshow' or params.get('mode') or params.get('interval'):
        cfg = load_slideshow_config()
        if 'mode' in params:
            cfg['mode'] = params['mode']
        if 'interval' in params:
            try:
                cfg['interval'] = int(params['interval'])
            except (ValueError, TypeError):
                pass
        if 'selected_images' in params:
            cfg['selected_images'] = params['selected_images']
        if 'fit' in params:
            cfg['fit'] = params['fit']
        save_slideshow_config(cfg)

    # Check if monitor 1 and monitor 2 targets are specified explicitly
    target1_raw = params.get('monitor1') or params.get('target1')
    target2_raw = params.get('monitor2') or params.get('target2')

    if not target1_raw:
        if action_type == 'slideshow':
            target1_raw = 'slideshow'
        elif 'image1' in params or action_type == 'image':
            target1_raw = {'type': 'image', 'image': params.get('image1', '')}
        else:
            target1_raw = {'type': 'website', 'url': params.get('url1', params.get('url', ''))}

    if not target2_raw:
        if action_type == 'slideshow':
            target2_raw = 'slideshow'
        elif 'image2' in params and params.get('image2'):
            target2_raw = {'type': 'image', 'image': params.get('image2', '')}
        elif 'url2' in params and params.get('url2') is not None:
            target2_raw = {'type': 'website', 'url': params.get('url2', '')}
        else:
            target2_raw = target1_raw

    url1 = _resolve_target(target1_raw, '1', params)
    url2 = _resolve_target(target2_raw, '2', params)

    cmd = [SCRIPT_PATH]
    if monitor == '1':
        cmd.append(url1)
        msg = "Updated Monitor 1"
    elif monitor == '2':
        cmd.extend(['', url2])
        msg = "Updated Monitor 2"
    else:
        cmd.extend([url1, url2])
        msg = "Updated both monitors with selected configuration"

    success, res = execute_display_command(cmd)
    if success:
        display_state.update({
            "status": "running",
            "mode": action_type if action_type in ['slideshow', 'website', 'image'] else 'mixed',
            "monitor": monitor,
            "updated_at": datetime.now().isoformat(),
            "last_message": msg
        })
        return True, msg
    return False, f"Failed to start display: {res}"

# ----------------------------------------------------------------------
# Background Time Scheduler
# ----------------------------------------------------------------------

last_triggered_minute = ""

def scheduler_worker():
    """Background worker that executes scheduled time events"""
    global last_triggered_minute
    while True:
        try:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M") # "14:30"
            current_day_str = now.strftime("%a").lower() # "mon", "tue", etc.

            # Only trigger once per minute
            minute_key = now.strftime("%Y-%m-%d %H:%M")
            if minute_key != last_triggered_minute:
                schedules = load_schedules()
                for sch in schedules:
                    if not sch.get("enabled", True):
                        continue
                    
                    target_time = sch.get("time", "")
                    days = sch.get("days", [])
                    
                    # Check time match and day match (if days specified)
                    if target_time == current_time_str:
                        if not days or current_day_str in [d.lower() for d in days]:
                            action = sch.get("action", "slideshow")
                            params = sch.get("params", {})
                            print(f"[SCHEDULER] Triggering schedule: {sch.get('name', 'Unnamed')} -> {action} at {current_time_str}")
                            trigger_display_action(action, params)

                last_triggered_minute = minute_key
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}", file=sys.stderr)

        time.sleep(15)

# Start scheduler thread
scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
scheduler_thread.start()

# ----------------------------------------------------------------------
# HTTP Web Routes
# ----------------------------------------------------------------------

@app.route('/')
def index():
    """Render the main control panel dashboard"""
    return render_template('index.html')

@app.route('/viewer')
@app.route('/slideshow')
def viewer():
    """Render the kiosk fullscreen image slideshow / single image viewer"""
    return render_template('viewer.html')

# ----------------------------------------------------------------------
# REST API Endpoints
# ----------------------------------------------------------------------

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system and display runtime status"""
    schedules = load_schedules()
    images = load_images()
    websites = load_websites()
    return jsonify({
        "success": True,
        "state": display_state,
        "counts": {
            "websites": len(websites),
            "images": len(images),
            "schedules": len(schedules),
            "active_schedules": len([s for s in schedules if s.get('enabled', True)])
        },
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# --- Websites API ---

@app.route('/api/websites', methods=['GET'])
def get_websites():
    """Get the list of websites"""
    return jsonify(load_websites())

@app.route('/api/websites', methods=['POST'])
def add_website():
    """Add a new website"""
    data = request.json or {}
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()

    if not name:
        return jsonify({"success": False, "error": "Website name is required"}), 400

    websites = load_websites()
    new_website = {
        "id": str(uuid.uuid4()),
        "name": name,
        "url": url,
        "is_default": False,
        "created_at": datetime.now().isoformat()
    }
    websites.append(new_website)
    save_websites(websites)
    return jsonify({"success": True, "websites": websites, "website": new_website})

@app.route('/api/websites/<int:index>', methods=['DELETE'])
def delete_website(index):
    """Delete a website by index"""
    websites = load_websites()
    if 0 <= index < len(websites):
        deleted = websites.pop(index)
        save_websites(websites)
        return jsonify({"success": True, "websites": websites, "deleted": deleted})
    return jsonify({"success": False, "error": "Invalid index"}), 400

# --- Images API ---

@app.route('/api/images', methods=['GET'])
def get_images():
    """Get the list of uploaded images"""
    return jsonify(load_images())

@app.route('/api/images', methods=['POST'])
def upload_image():
    """Upload a new image file"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files['file']
    name = request.form.get('name', '').strip()

    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False, 
            "error": f"File type not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    try:
        filename = secure_filename(file.filename)
        name_part, ext = os.path.splitext(filename)
        unique_filename = f"{name_part}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

        file.save(filepath)

        images = load_images()
        image_name = name if name else name_part
        new_image = {
            "id": str(uuid.uuid4()),
            "name": image_name,
            "filename": unique_filename,
            "original_filename": filename,
            "uploaded_at": datetime.now().isoformat(),
            "url": f"/api/images/{unique_filename}"
        }
        images.append(new_image)
        save_images(images)

        return jsonify({"success": True, "images": images, "image": new_image})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/<int:index>', methods=['DELETE'])
def delete_image(index):
    """Delete an image by index"""
    images = load_images()
    if 0 <= index < len(images):
        image = images.pop(index)
        
        # Delete file from primary upload folder and legacy location if exists
        for folder in [UPLOAD_FOLDER, LEGACY_UPLOADS]:
            filepath = os.path.join(folder, image.get('filename', ''))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"[WARN] Error deleting file {filepath}: {e}", file=sys.stderr)

        save_images(images)

        # Update slideshow config if the deleted image was selected
        cfg = load_slideshow_config()
        if image.get('id') in cfg.get('selected_images', []):
            cfg['selected_images'] = [i for i in cfg['selected_images'] if i != image.get('id')]
            save_slideshow_config(cfg)

        return jsonify({"success": True, "images": images})
    return jsonify({"success": False, "error": "Invalid index"}), 400

@app.route('/api/images/<filename>')
def serve_image(filename):
    """Serve uploaded images with cache control"""
    # Check upload folder, fallback to legacy
    if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
        return send_from_directory(UPLOAD_FOLDER, filename)
    elif os.path.exists(os.path.join(LEGACY_UPLOADS, filename)):
        return send_from_directory(LEGACY_UPLOADS, filename)
    return jsonify({"error": "Image not found"}), 404

# --- Slideshow & Viewer API ---

@app.route('/api/slideshow', methods=['GET'])
def get_slideshow():
    """Get slideshow configuration and available images"""
    config = load_slideshow_config()
    images = load_images()
    return jsonify({
        "success": True,
        "config": config,
        "total_images": len(images)
    })

@app.route('/api/slideshow', methods=['POST'])
def update_slideshow():
    """Update slideshow settings"""
    data = request.json or {}
    config = load_slideshow_config()

    if 'mode' in data and data['mode'] in ['random', 'sequential']:
        config['mode'] = data['mode']
    if 'interval' in data:
        try:
            config['interval'] = max(2, int(data['interval']))
        except ValueError:
            pass
    if 'transition' in data:
        config['transition'] = data['transition']
    if 'fit' in data:
        config['fit'] = data['fit']
    if 'selected_images' in data and isinstance(data['selected_images'], list):
        config['selected_images'] = data['selected_images']
    if 'background_color' in data:
        config['background_color'] = data['background_color']

    save_slideshow_config(config)
    return jsonify({"success": True, "config": config})

@app.route('/api/viewer/data', methods=['GET'])
def get_viewer_data():
    """Endpoint consumed by the fullscreen kiosk slideshow page"""
    config = load_slideshow_config()
    all_images = load_images()

    # Filter selected images if specified
    selected_ids = set(config.get('selected_images', []))
    if selected_ids:
        filtered = [img for img in all_images if img.get('id') in selected_ids]
        images = filtered if filtered else all_images
    else:
        images = all_images

    # Format images list for the viewer
    image_list = [{
        "id": img.get("id"),
        "name": img.get("name"),
        "url": f"/api/images/{img.get('filename')}"
    } for img in images]

    return jsonify({
        "success": True,
        "config": config,
        "images": image_list,
        "state": display_state
    })

# --- Schedules API ---

@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Get list of automated display schedules"""
    return jsonify(load_schedules())

@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    """Add a new scheduled display change"""
    data = request.json or {}
    name = data.get('name', 'Schedule').strip()
    time_val = data.get('time', '').strip() # "HH:MM"
    action = data.get('action', 'slideshow') # "slideshow", "website", "blank", "wake"
    days = data.get('days', ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    params = data.get('params', {})

    if not time_val or len(time_val.split(':')) != 2:
        return jsonify({"success": False, "error": "Valid time in HH:MM format is required"}), 400

    schedules = load_schedules()
    new_schedule = {
        "id": str(uuid.uuid4()),
        "name": name,
        "time": time_val,
        "action": action,
        "days": days,
        "params": params,
        "enabled": True,
        "created_at": datetime.now().isoformat()
    }
    schedules.append(new_schedule)
    save_schedules(schedules)
    return jsonify({"success": True, "schedules": schedules, "schedule": new_schedule})

@app.route('/api/schedules/<schedule_id>/toggle', methods=['PUT'])
def toggle_schedule(schedule_id):
    """Toggle a schedule enabled/disabled"""
    schedules = load_schedules()
    found = False
    for s in schedules:
        if s.get('id') == schedule_id:
            s['enabled'] = not s.get('enabled', True)
            found = True
            break
    if found:
        save_schedules(schedules)
        return jsonify({"success": True, "schedules": schedules})
    return jsonify({"success": False, "error": "Schedule not found"}), 404

@app.route('/api/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete a schedule"""
    schedules = load_schedules()
    updated = [s for s in schedules if s.get('id') != schedule_id]
    if len(updated) != len(schedules):
        save_schedules(updated)
        return jsonify({"success": True, "schedules": updated})
    return jsonify({"success": False, "error": "Schedule not found"}), 404

# --- Display Control Endpoints ---

@app.route('/api/display', methods=['POST'])
def start_display():
    """Start display with Website, Image, or Slideshow"""
    data = request.json or {}
    mode = data.get('mode', '')

    # Automatic mode detection if not explicitly passed
    if mode == 'slideshow' or data.get('slideshow'):
        success, msg = trigger_display_action('slideshow', data)
    elif 'image1' in data or 'image2' in data or mode == 'image':
        success, msg = trigger_display_action('image', data)
    else:
        success, msg = trigger_display_action('website', data)

    if success:
        return jsonify({"success": True, "message": msg, "state": display_state})
    return jsonify({"success": False, "error": msg}), 500

@app.route('/api/display', methods=['DELETE'])
def stop_display():
    """Stop/Blank display"""
    success, msg = trigger_display_action('blank')
    if success:
        return jsonify({"success": True, "message": msg, "state": display_state})
    return jsonify({"success": False, "error": msg}), 500

@app.route('/api/display/wake', methods=['POST'])
def wake_display():
    """Wake display"""
    success, msg = trigger_display_action('wake')
    if success:
        return jsonify({"success": True, "message": msg, "state": display_state})
    return jsonify({"success": False, "error": msg}), 500

# ----------------------------------------------------------------------
# Application Entry Point
# ----------------------------------------------------------------------

if __name__ == '__main__':
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    print(f"🚀 Starting Pi Display Control Server on port {PORT}...")
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"🖼️ Uploads directory: {UPLOAD_FOLDER}")
    print(f"⚙️ Scripts: start={SCRIPT_PATH}, blank={BLANK_SCREEN_PATH}, wake={WAKE_SCREEN_PATH}")
    app.run(host='0.0.0.0', port=PORT, debug=debug)
