"""
Websites, Images, and Slideshow REST API endpoints.
"""

import os
import sys
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from services.storage import (
    UPLOAD_FOLDER,
    LEGACY_UPLOADS,
    ALLOWED_EXTENSIONS,
    load_websites,
    save_websites,
    load_images,
    save_images,
    load_slideshow_config,
    save_slideshow_config,
    allowed_file
)
from services.display_service import display_state

api_media_bp = Blueprint('api_media', __name__)

# --- Websites API ---

@api_media_bp.route('/api/websites', methods=['GET'])
def get_websites():
    """Get the list of websites"""
    return jsonify(load_websites())

@api_media_bp.route('/api/websites', methods=['POST'])
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

@api_media_bp.route('/api/websites/<int:index>', methods=['DELETE'])
def delete_website(index):
    """Delete a website by index"""
    websites = load_websites()
    if 0 <= index < len(websites):
        deleted = websites.pop(index)
        save_websites(websites)
        return jsonify({"success": True, "websites": websites, "deleted": deleted})
    return jsonify({"success": False, "error": "Invalid index"}), 400

# --- Images API ---

@api_media_bp.route('/api/images', methods=['GET'])
def get_images():
    """Get the list of uploaded images"""
    return jsonify(load_images())

@api_media_bp.route('/api/images', methods=['POST'])
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

@api_media_bp.route('/api/images/<int:index>', methods=['DELETE'])
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

@api_media_bp.route('/api/images/<filename>')
def serve_image(filename):
    """Serve uploaded images with cache control"""
    if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
        return send_from_directory(UPLOAD_FOLDER, filename)
    elif os.path.exists(os.path.join(LEGACY_UPLOADS, filename)):
        return send_from_directory(LEGACY_UPLOADS, filename)
    return jsonify({"error": "Image not found"}), 404

# --- Slideshow & Viewer API ---

@api_media_bp.route('/api/slideshow', methods=['GET'])
def get_slideshow():
    """Get slideshow configuration and available images"""
    config = load_slideshow_config()
    images = load_images()
    return jsonify({
        "success": True,
        "config": config,
        "total_images": len(images)
    })

@api_media_bp.route('/api/slideshow', methods=['POST'])
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

@api_media_bp.route('/api/viewer/data', methods=['GET'])
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
