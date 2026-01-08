#!/usr/bin/env python3
"""
Raspberry Pi Display Control Interface
Web-based control panel for managing display scripts
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

app = Flask(__name__)

# Get the directory where app.py is located
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration - support environment variables for Docker
HOME_DIR = os.getenv('WORK_DIR', os.path.expanduser("~"))
SCRIPT_PATH = os.getenv('SCRIPT_PATH', os.path.join(APP_DIR, "start.sh"))
BLANK_SCREEN_PATH = os.getenv('BLANK_SCREEN_PATH', os.path.join(APP_DIR, "blank-screen.sh"))
WAKE_SCREEN_PATH = os.getenv('WAKE_SCREEN_PATH', os.path.join(APP_DIR, "wake-screen.sh"))
CONFIG_FILE = os.getenv('CONFIG_FILE', "/data/websites.json")

# Fallback to local config if /data doesn't exist (for local development)
if not os.path.exists('/data') and CONFIG_FILE.startswith('/data'):
    CONFIG_FILE = "websites.json"

# Image upload configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(CONFIG_FILE), 'uploads', 'images'))
IMAGES_CONFIG_FILE = os.getenv('IMAGES_CONFIG_FILE', os.path.join(os.path.dirname(CONFIG_FILE), 'images.json'))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_images():
    """Load the list of uploaded images from config file"""
    if os.path.exists(IMAGES_CONFIG_FILE):
        with open(IMAGES_CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        return []

def save_images(images):
    """Save the list of images to config file"""
    with open(IMAGES_CONFIG_FILE, 'w') as f:
        json.dump(images, f, indent=2)

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
    """Start the display script with URL(s) or image path(s) for monitor(s)"""
    data = request.json
    url = data.get('url', '')  # For backward compatibility
    url1 = data.get('url1', url)  # Monitor 1 URL
    url2 = data.get('url2', None)  # Monitor 2 URL (optional)
    image1 = data.get('image1', None)  # Monitor 1 image filename
    image2 = data.get('image2', None)  # Monitor 2 image filename
    monitor = data.get('monitor', 'both')  # '1', '2', or 'both'
    
    # If images are provided, use file:// protocol for local images
    # Images take precedence over URLs if both are provided
    if image1:
        url1 = f"file://{os.path.join(UPLOAD_FOLDER, image1)}"
    if image2:
        url2 = f"file://{os.path.join(UPLOAD_FOLDER, image2)}"
    
    # Build the command based on monitor selection
    cmd = [SCRIPT_PATH]
    
    if monitor == '1':
        # Only monitor 1
        if url1:
            cmd.append(url1)
    elif monitor == '2':
        # Only monitor 2 - need to pass empty string for monitor 1, then url2
        cmd.append('')  # Monitor 1 gets default
        if url2:
            cmd.append(url2)
        else:
            cmd.append(url1 if url1 else '')  # Use url1 if url2 not provided
    else:
        # Both monitors
        if url1:
            cmd.append(url1)
        else:
            cmd.append('')  # Empty string for default
        
        if url2 is not None:
            cmd.append(url2)
        elif url1:
            cmd.append(url1)  # If url2 not provided, use url1 for both
    
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
            cwd=APP_DIR
        )
        
        # Build success message
        display_name1 = image1 if image1 else (url1 if url1 else 'default (Autodarts)')
        display_name2 = image2 if image2 else (url2 if url2 else display_name1)
        
        if monitor == '1':
            message = f"Started display on Monitor 1 with: {display_name1}"
        elif monitor == '2':
            message = f"Started display on Monitor 2 with: {display_name2}"
        else:
            message = f"Started display on both monitors - Monitor 1: {display_name1}, Monitor 2: {display_name2}"
        
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
            cwd=APP_DIR
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
            cwd=APP_DIR
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

@app.route('/api/images', methods=['GET'])
def get_images():
    """Get the list of uploaded images"""
    return jsonify(load_images())

@app.route('/api/images', methods=['POST'])
def upload_image():
    """Upload a new image"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    
    file = request.files['file']
    name = request.form.get('name', '').strip()
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "File type not allowed. Allowed types: " + ", ".join(ALLOWED_EXTENSIONS)}), 400
    
    if file:
        # Generate unique filename
        filename = secure_filename(file.filename)
        name_part, ext = os.path.splitext(filename)
        unique_filename = f"{name_part}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save file
        file.save(filepath)
        
        # Add to images list
        images = load_images()
        image_name = name if name else name_part
        new_image = {
            "id": str(uuid.uuid4()),
            "name": image_name,
            "filename": unique_filename,
            "original_filename": filename,
            "uploaded_at": datetime.now().isoformat()
        }
        images.append(new_image)
        save_images(images)
        
        return jsonify({"success": True, "images": images, "image": new_image})
    
    return jsonify({"success": False, "error": "Upload failed"}), 500

@app.route('/api/images/<int:index>', methods=['DELETE'])
def delete_image(index):
    """Delete an image by index"""
    images = load_images()
    if 0 <= index < len(images):
        image = images[index]
        # Delete the file
        filepath = os.path.join(UPLOAD_FOLDER, image['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        # Remove from list
        images.pop(index)
        save_images(images)
        return jsonify({"success": True, "images": images})
    return jsonify({"success": False, "error": "Invalid index"}), 400

@app.route('/api/images/<filename>')
def serve_image(filename):
    """Serve uploaded images"""
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Create config directory if needed
    config_dir = os.path.dirname(CONFIG_FILE)
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Ensure images config directory exists
    images_config_dir = os.path.dirname(IMAGES_CONFIG_FILE)
    if images_config_dir and not os.path.exists(images_config_dir):
        os.makedirs(images_config_dir, exist_ok=True)
    
    # Get port from environment or default to 5000
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    
    print(f"Starting control server...")
    print(f"Script path: {SCRIPT_PATH}")
    print(f"Blank screen path: {BLANK_SCREEN_PATH}")
    print(f"Wake screen path: {WAKE_SCREEN_PATH}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"Images config file: {IMAGES_CONFIG_FILE}")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Access the control panel at: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

