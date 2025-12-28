#!/usr/bin/env python3
"""
Raspberry Pi Display Control Interface
Web-based control panel for managing display scripts
"""

from flask import Flask, render_template, request, jsonify
import subprocess
import json
import os
from pathlib import Path

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

def load_websites():
    """Load the list of websites from config file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default websites
        default_websites = [
            {"name": "Autodarts Board", "url": "", "is_default": True},
            {"name": "8-bit Website", "url": "https://8bit.website.com", "is_default": False}
        ]
        save_websites(default_websites)
        return default_websites

def save_websites(websites):
    """Save the list of websites to config file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(websites, f, indent=2)

@app.route('/')
def index():
    """Render the main control page"""
    return render_template('index.html')

@app.route('/api/websites', methods=['GET'])
def get_websites():
    """Get the list of websites"""
    return jsonify(load_websites())

@app.route('/api/websites', methods=['POST'])
def add_website():
    """Add a new website"""
    data = request.json
    websites = load_websites()
    
    # Add new website
    new_website = {
        "name": data.get('name', 'New Website'),
        "url": data.get('url', ''),
        "is_default": False
    }
    websites.append(new_website)
    save_websites(websites)
    
    return jsonify({"success": True, "websites": websites})

@app.route('/api/websites/<int:index>', methods=['DELETE'])
def delete_website(index):
    """Delete a website by index"""
    websites = load_websites()
    if 0 <= index < len(websites):
        websites.pop(index)
        save_websites(websites)
        return jsonify({"success": True, "websites": websites})
    return jsonify({"success": False, "error": "Invalid index"}), 400

@app.route('/api/display', methods=['POST'])
def start_display():
    """Start the display script with a URL"""
    data = request.json
    url = data.get('url', '')
    
    # Build the command
    if url:
        cmd = [SCRIPT_PATH, url]
    else:
        cmd = [SCRIPT_PATH]
    
    try:
        # Check if script exists
        if not os.path.exists(SCRIPT_PATH):
            return jsonify({
                "success": False,
                "error": f"Script not found at {SCRIPT_PATH}"
            }), 404
        
        # Execute the script
        # Using nohup to run in background and redirect output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HOME_DIR
        )
        
        return jsonify({
            "success": True,
            "message": f"Started display with URL: {url if url else 'default (Autodarts)'}",
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
        # Check if blank-screen.sh exists
        if not os.path.exists(BLANK_SCREEN_PATH):
            return jsonify({
                "success": False,
                "error": f"Script not found at {BLANK_SCREEN_PATH}"
            }), 404
        
        # Execute blank-screen.sh
        process = subprocess.Popen(
            [BLANK_SCREEN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HOME_DIR
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
        # Check if wake-screen.sh exists
        if not os.path.exists(WAKE_SCREEN_PATH):
            return jsonify({
                "success": False,
                "error": f"Script not found at {WAKE_SCREEN_PATH}"
            }), 404
        
        # Execute wake-screen.sh
        process = subprocess.Popen(
            [WAKE_SCREEN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HOME_DIR
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
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Create config directory if needed
    config_dir = os.path.dirname(CONFIG_FILE)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    # Get port from environment or default to 5000
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    
    print(f"Starting control server...")
    print(f"Script path: {SCRIPT_PATH}")
    print(f"Blank screen path: {BLANK_SCREEN_PATH}")
    print(f"Wake screen path: {WAKE_SCREEN_PATH}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"Access the control panel at: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

