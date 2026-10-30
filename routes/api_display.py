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
    get_monitor_default_content,
    set_monitor_default_content,
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
    Get discovered monitors, their active geometry/rotation, and saved startup defaults (rotations & content).
    """
    connected = get_connected_monitors()
    rot_defaults = {
        "1": get_monitor_rotation("1", "left"),
        "2": get_monitor_rotation("2", "right")
    }
    content_defaults = {
        "1": get_monitor_default_content("1"),
        "2": get_monitor_default_content("2")
    }
    defaults = {
        "1": rot_defaults["1"],
        "2": rot_defaults["2"],
        "rotations": rot_defaults,
        "content": content_defaults
    }

    monitors_data = []
    for idx, m in enumerate(connected, 1):
        mon_idx_str = str(idx)
        m_copy = dict(m)
        m_copy["index"] = idx
        m_copy["connected"] = True
        m_copy["current_rotation"] = m.get("rotation", "normal")
        m_copy["default_rotation"] = rot_defaults.get(mon_idx_str, "normal")
        m_copy["default_content"] = content_defaults.get(mon_idx_str, {})
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
                "2": get_monitor_rotation("2"),
                "rotations": {
                    "1": get_monitor_rotation("1"),
                    "2": get_monitor_rotation("2")
                },
                "content": {
                    "1": get_monitor_default_content("1"),
                    "2": get_monitor_default_content("2")
                }
            }
        })
    return jsonify({"success": False, "error": msg}), 500

@api_display_bp.route('/api/display/default-content', methods=['POST'])
def save_default_content():
    """
    Save persistent default site or wallpaper content for startup and wake.
    Payload:
      - monitor: "1", "2", or "both"
      - content: {"type": "website"|"image"|"slideshow", ...}
      - contents: {"1": {...}, "2": {...}}
      - apply_now: boolean (default False)
    """
    data = request.json or {}
    apply_now = bool(data.get('apply_now', False))
    monitor = str(data.get('monitor', '1'))
    content = data.get('content')
    contents = data.get('contents')

    try:
        if contents and isinstance(contents, dict):
            for m_id, m_content in contents.items():
                if str(m_id) in ["1", "2"]:
                    set_monitor_default_content(str(m_id), m_content)
        elif content and isinstance(content, dict):
            if monitor == "both":
                set_monitor_default_content("1", content)
                set_monitor_default_content("2", content)
            elif monitor in ["1", "2"]:
                set_monitor_default_content(monitor, content)
            else:
                return jsonify({"success": False, "error": f"Invalid monitor id '{monitor}'"}), 400
        else:
            return jsonify({"success": False, "error": "Missing content or contents dictionary"}), 400

        msg = "Default monitor site/wallpaper saved successfully"

        if apply_now:
            c1 = get_monitor_default_content("1")
            c2 = get_monitor_default_content("2")
            if monitor == "1":
                ok, apply_msg = trigger_display_action("mixed", {"monitor": "1", "monitor1": c1})
            elif monitor == "2":
                ok, apply_msg = trigger_display_action("mixed", {"monitor": "2", "monitor2": c2})
            else:
                ok, apply_msg = trigger_display_action("mixed", {"monitor": "both", "monitor1": c1, "monitor2": c2})
            if not ok:
                return jsonify({"success": False, "error": f"Saved, but failed to apply: {apply_msg}"}), 500
            msg += f" and applied: {apply_msg}"

        return jsonify({
            "success": True,
            "message": msg,
            "defaults": {
                "1": get_monitor_rotation("1"),
                "2": get_monitor_rotation("2"),
                "rotations": {
                    "1": get_monitor_rotation("1"),
                    "2": get_monitor_rotation("2")
                },
                "content": {
                    "1": get_monitor_default_content("1"),
                    "2": get_monitor_default_content("2")
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_display_bp.route('/api/display/defaults', methods=['POST'])
def save_defaults():
    """
    Save default rotations and/or default site/wallpaper content for startup / wake.
    Payload:
      - rotations: optional map {"1": "left", "2": "right"}
      - content: optional map {"1": {...}, "2": {...}}
      - apply_now: boolean (default False)
      - restart_browser: boolean (default True)
    """
    data = request.json or {}
    rotations = data.get('rotations')
    content = data.get('content') or data.get('contents')
    apply_now = bool(data.get('apply_now', False))
    restart_browser = bool(data.get('restart_browser', True))

    if not rotations and not content:
        return jsonify({"success": False, "error": "Missing rotations or content in request"}), 400

    messages = []

    # Handle rotations if provided
    if rotations and isinstance(rotations, dict):
        for mon_id, rot in rotations.items():
            if rot not in VALID_ROTATIONS:
                return jsonify({"success": False, "error": f"Invalid rotation '{rot}' for Monitor {mon_id}. Valid choices: {VALID_ROTATIONS}"}), 400
            set_default_rotation(str(mon_id), rot)
        messages.append("Default monitor rotations saved")

    # Handle content if provided
    if content and isinstance(content, dict):
        for mon_id, mon_content in content.items():
            if str(mon_id) in ["1", "2"]:
                set_monitor_default_content(str(mon_id), mon_content)
        messages.append("Default monitor site/wallpaper saved")

    msg = " and ".join(messages) + " successfully"

    if apply_now:
        if rotations:
            success, apply_msg = apply_display_rotations(rotations, save_default=False, restart_chromium=False)
            if not success:
                return jsonify({"success": False, "error": f"Defaults saved, but failed to apply rotations: {apply_msg}"}), 500
        if restart_browser or content:
            c1 = get_monitor_default_content("1")
            c2 = get_monitor_default_content("2")
            ok, apply_msg = trigger_display_action("mixed", {"monitor": "both", "monitor1": c1, "monitor2": c2})
            if not ok:
                return jsonify({"success": False, "error": f"Defaults saved, but failed to apply display: {apply_msg}"}), 500
            msg += f" and applied: {apply_msg}"

    return jsonify({
        "success": True,
        "message": msg,
        "defaults": {
            "1": get_monitor_rotation("1"),
            "2": get_monitor_rotation("2"),
            "rotations": {
                "1": get_monitor_rotation("1"),
                "2": get_monitor_rotation("2")
            },
            "content": {
                "1": get_monitor_default_content("1"),
                "2": get_monitor_default_content("2")
            }
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
                "2": get_monitor_rotation("2"),
                "rotations": {
                    "1": get_monitor_rotation("1"),
                    "2": get_monitor_rotation("2")
                },
                "content": {
                    "1": get_monitor_default_content("1"),
                    "2": get_monitor_default_content("2")
                }
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
