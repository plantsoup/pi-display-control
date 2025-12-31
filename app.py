#!/usr/bin/env python3
"""
Raspberry Pi Display Control Interface
Web-based control panel for managing display scripts
"""

from flask import Flask, render_template, request, jsonify, make_response
from functools import lru_cache, wraps
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Configuration - support environment variables for Docker
HOME_DIR = os.getenv('WORK_DIR', os.path.expanduser("~"))
SCRIPT_PATH = os.getenv('SCRIPT_PATH', os.path.join(HOME_DIR, "start.sh"))
BLANK_SCREEN_PATH = os.getenv('BLANK_SCREEN_PATH', os.path.join(HOME_DIR, "blank-screen.sh"))
WAKE_SCREEN_PATH = os.getenv('WAKE_SCREEN_PATH', os.path.join(HOME_DIR, "wake-screen.sh"))
CONFIG_FILE = os.getenv('CONFIG_FILE', "/data/websites.json")

# Fallback to local config if /data doesn't exist (for local development)
if not os.path.exists('/data') and CONFIG_FILE.startswith('/data'):
    CONFIG_FILE = "websites.json"

# Cache for websites (cleared on write operations)
_websites_cache = None
_cache_timestamp = None

def get_cache_headers(max_age=60):
    """Generate cache control headers"""
    return {
        'Cache-Control': f'private, max-age={max_age}',
        'Content-Type': 'application/json'
    }

def load_websites(use_cache=True):
    """Load the list of websites from config file with caching"""
    global _websites_cache, _cache_timestamp
    
    if use_cache and _websites_cache is not None:
        return _websites_cache
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                websites = json.load(f)
        else:
            # Default websites
            websites = [
                {"name": "Autodarts Board", "url": "", "is_default": True},
                {"name": "8-bit Website", "url": "https://8bit.website.com", "is_default": False}
            ]
            save_websites(websites, update_cache=False)
        
        _websites_cache = websites
        _cache_timestamp = datetime.now()
        return websites
    except (json.JSONDecodeError, IOError) as e:
        return []

def save_websites(websites, update_cache=True):
    """Save the list of websites to config file"""
    global _websites_cache
    
    try:
        config_dir = os.path.dirname(CONFIG_FILE)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(websites, f, indent=2)
        
        if update_cache:
            _websites_cache = websites
        return True
    except IOError:
        return False

def clear_websites_cache():
    """Clear the websites cache"""
    global _websites_cache
    _websites_cache = None

@app.route('/')
def index():
    """Render the main control page"""
    response = make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'public, max-age=300'  # Cache HTML for 5 minutes
    return response

@app.route('/api/websites', methods=['GET'])
def get_websites():
    """Get the list of websites"""
    websites = load_websites()
    response = jsonify(websites)
    response.headers.update(get_cache_headers(max_age=30))
    return response

@app.route('/api/websites', methods=['POST'])
def add_website():
    """Add a new website"""
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400
    
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"success": False, "error": "Website name is required"}), 400
    
    websites = load_websites(use_cache=False)
    
    # Add new website
    new_website = {
        "name": name,
        "url": data.get('url', '').strip(),
        "is_default": False
    }
    websites.append(new_website)
    
    if save_websites(websites):
        return jsonify({"success": True, "websites": websites})
    else:
        return jsonify({"success": False, "error": "Failed to save website"}), 500

@app.route('/api/websites/<int:index>', methods=['DELETE'])
def delete_website(index):
    """Delete a website by index"""
    websites = load_websites(use_cache=False)
    
    if 0 <= index < len(websites):
        websites.pop(index)
        if save_websites(websites):
            return jsonify({"success": True, "websites": websites})
        else:
            return jsonify({"success": False, "error": "Failed to delete website"}), 500
    
    return jsonify({"success": False, "error": "Invalid index"}), 400

def build_command(monitor, url1, url2):
    """Build command array based on monitor selection"""
    cmd = [SCRIPT_PATH]
    
    if monitor == '1':
        if url1:
            cmd.append(url1)
    elif monitor == '2':
        cmd.append('')  # Monitor 1 gets default
        cmd.append(url2 if url2 else (url1 if url1 else ''))
    else:  # both
        # For both monitors with same URL (url2 is None), pass url1 once
        # For both monitors with different URLs, pass both
        if url2 is not None:
            cmd.append(url1 if url1 else '')
            cmd.append(url2)
        else:
            # Both monitors same site - pass url1 once
            # start.sh should interpret single URL as both monitors
            cmd.append(url1 if url1 else '')
    
    return cmd

@app.route('/api/display', methods=['POST'])
def start_display():
    """Start the display script with URL(s) for monitor(s)"""
    data = request.get_json() or {}
    
    url = data.get('url', '')  # For backward compatibility
    url1 = data.get('url1', url).strip()
    url2 = data.get('url2')
    if url2:
        url2 = url2.strip()
    monitor = data.get('monitor', 'both')
    
    if monitor not in ('1', '2', 'both'):
        return jsonify({"success": False, "error": "Invalid monitor selection"}), 400
    
    try:
        if not os.path.exists(SCRIPT_PATH):
            return jsonify({
                "success": False,
                "error": f"Script not found at {SCRIPT_PATH}"
            }), 404
        
        cmd = build_command(monitor, url1, url2)
        
        # Execute the script (don't wait for completion)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HOME_DIR,
            start_new_session=True  # Detach from parent process
        )
        
        # Build success message
        if monitor == '1':
            message = f"Started display on Monitor 1 with: {url1 if url1 else 'default (Autodarts)'}"
        elif monitor == '2':
            display_url = url2 if url2 else (url1 if url1 else 'default (Autodarts)')
            message = f"Started display on Monitor 2 with: {display_url}"
        else:
            msg1 = url1 if url1 else 'default (Autodarts)'
            msg2 = url2 if url2 else msg1
            message = f"Started display on both monitors - Monitor 1: {msg1}, Monitor 2: {msg2}"
        
        return jsonify({
            "success": True,
            "message": message,
            "pid": process.pid
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/display', methods=['DELETE'])
def stop_display():
    """Stop the currently running display (blank screen)"""
    try:
        if not os.path.exists(BLANK_SCREEN_PATH):
            return jsonify({
                "success": False,
                "error": f"Script not found at {BLANK_SCREEN_PATH}"
            }), 404
        
        process = subprocess.Popen(
            [BLANK_SCREEN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HOME_DIR,
            start_new_session=True
        )
        
        return jsonify({
            "success": True,
            "message": "Display blanked",
            "pid": process.pid
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/display/wake', methods=['POST'])
def wake_display():
    """Wake the display"""
    try:
        if not os.path.exists(WAKE_SCREEN_PATH):
            return jsonify({
                "success": False,
                "error": f"Script not found at {WAKE_SCREEN_PATH}"
            }), 404
        
        process = subprocess.Popen(
            [WAKE_SCREEN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HOME_DIR,
            start_new_session=True
        )
        
        return jsonify({
            "success": True,
            "message": "Display woken",
            "pid": process.pid
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    config_dir = os.path.dirname(CONFIG_FILE)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    
    print(f"Starting control server...")
    print(f"Script path: {SCRIPT_PATH}")
    print(f"Blank screen path: {BLANK_SCREEN_PATH}")
    print(f"Wake screen path: {WAKE_SCREEN_PATH}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"Access the control panel at: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
