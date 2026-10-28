"""
Display control, monitor orientation, and system status REST API endpoints.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from services.storage import (
    load_websites,
    load_images,
    load_schedules,
    load_display_config,
    save_display_config,
    get_monitor_rotation,
    set_default_rotation,
    VALID_ROTATIONS,
    ROTATION_METADATA
)
from services.display_service import display_state, trigger_display_action
from display import (
    get_connected_monitors,
    apply_monitor_rotation,
    apply_display_rotations,
    reset_display_to_defaults
)

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

@api_display_bp.route('/api/display/monitors', methods=['GET'])
def get_monitors():
    """
    Get discovered monitors, their active geometry/rotation, and saved startup defaults.
    """
    connected = get_connected_monitors()
    defaults = {
        "1": get_monitor_rotation("1", "left"),
        "2": get_monitor_rotation("2", "right")
    }

    monitors_data = []
    for idx, m in enumerate(connected, 1):
        mon_idx_str = str(idx)
        m_copy = dict(m)
        m_copy["index"] = idx
        m_copy["connected"] = True
        m_copy["current_rotation"] = m.get("rotation", "normal")
        m_copy["default_rotation"] = defaults.get(mon_idx_str, "normal")
        monitors_data.append(m_copy)

    return jsonify({
        "success": True,
        "monitors": monitors_data,
        "count": len(monitors_data),
        "defaults": defaults,
        "available_rotations": ROTATION_METADATA
    })

@api_display_bp.route('/api/display/rotate', methods=['POST'])
def rotate_display():
    """
    Rotate display on the fly and optionally save as default.
    Payload:
      - monitor: "1", "2", or "both"
      - rotation: "normal", "left", "right", or "inverted"
      - rotations: optional map {"1": "left", "2": "right"}
      - save_default: boolean (default False)
      - restart_browser: boolean (default True)
    """
    data = request.json or {}
    save_default = bool(data.get('save_default', False))
    restart_browser = bool(data.get('restart_browser', True))
    rotations = data.get('rotations')
    monitor = str(data.get('monitor', '1'))
    rotation = data.get('rotation')

    if rotations and isinstance(rotations, dict):
        success, msg = apply_display_rotations(rotations, save_default=save_default, restart_chromium=restart_browser)
    elif rotation:
        if monitor == "both":
            success, msg = apply_display_rotations({"1": rotation, "2": rotation}, save_default=save_default, restart_chromium=restart_browser)
        else:
            success, msg = apply_monitor_rotation(monitor, rotation, save_default=save_default, restart_chromium=restart_browser)
    else:
        return jsonify({"success": False, "error": "Missing rotation or rotations parameter"}), 400

    if success:
        return jsonify({
            "success": True,
            "message": msg,
            "defaults": {
                "1": get_monitor_rotation("1"),
                "2": get_monitor_rotation("2")
            }
        })
    return jsonify({"success": False, "error": msg}), 500

@api_display_bp.route('/api/display/defaults', methods=['POST'])
def save_defaults():
    """
    Save default rotations for startup / wake.
    Payload:
      - rotations: {"1": "left", "2": "right"}
      - apply_now: boolean (default False)
      - restart_browser: boolean (default True)
    """
    data = request.json or {}
    rotations = data.get('rotations', {})
    apply_now = bool(data.get('apply_now', False))
    restart_browser = bool(data.get('restart_browser', True))

    if not rotations or not isinstance(rotations, dict):
        return jsonify({"success": False, "error": "Invalid or missing rotations object"}), 400

    for mon_id, rot in rotations.items():
        if rot not in VALID_ROTATIONS:
            return jsonify({"success": False, "error": f"Invalid rotation '{rot}' for Monitor {mon_id}. Valid choices: {VALID_ROTATIONS}"}), 400
        set_default_rotation(str(mon_id), rot)

    msg = "Default monitor rotations saved successfully"
    if apply_now:
        success, apply_msg = apply_display_rotations(rotations, save_default=False, restart_chromium=restart_browser)
        if not success:
            return jsonify({"success": False, "error": f"Defaults saved, but failed to apply: {apply_msg}"}), 500
        msg += f" and applied: {apply_msg}"

    return jsonify({
        "success": True,
        "message": msg,
        "defaults": {
            "1": get_monitor_rotation("1"),
            "2": get_monitor_rotation("2")
        }
    })

@api_display_bp.route('/api/display/reset-defaults', methods=['POST'])
def reset_defaults():
    """Re-apply saved default orientations to all connected displays"""
    data = request.json or {}
    restart_browser = bool(data.get('restart_browser', True))
    success, msg = reset_display_to_defaults(restart_chromium=restart_browser)
    if success:
        return jsonify({
            "success": True,
            "message": msg,
            "defaults": {
                "1": get_monitor_rotation("1"),
                "2": get_monitor_rotation("2")
            }
        })
    return jsonify({"success": False, "error": msg}), 500

@api_display_bp.route('/api/display', methods=['POST'])
def start_display_route():
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
    """Wake display (restores displays to saved default rotations)"""
    success, msg = trigger_display_action('wake')
    if success:
        return jsonify({"success": True, "message": msg, "state": display_state})
    return jsonify({"success": False, "error": msg}), 500
