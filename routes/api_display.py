"""
Display control and system status REST API endpoints.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from services.storage import load_websites, load_images, load_schedules
from services.display_service import display_state, trigger_display_action

api_display_bp = Blueprint('api_display', __name__)

@api_display_bp.route('/api/status', methods=['GET'])
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

@api_display_bp.route('/api/display', methods=['POST'])
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

@api_display_bp.route('/api/display', methods=['DELETE'])
def stop_display():
    """Stop/Blank display"""
    success, msg = trigger_display_action('blank')
    if success:
        return jsonify({"success": True, "message": msg, "state": display_state})
    return jsonify({"success": False, "error": msg}), 500

@api_display_bp.route('/api/display/wake', methods=['POST'])
def wake_display():
    """Wake display"""
    success, msg = trigger_display_action('wake')
    if success:
        return jsonify({"success": True, "message": msg, "state": display_state})
    return jsonify({"success": False, "error": msg}), 500
