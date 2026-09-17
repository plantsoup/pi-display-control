"""
Schedules REST API endpoints.
Handles automated display event configuration, toggling, and management.
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from services.storage import load_schedules, save_schedules

api_schedules_bp = Blueprint('api_schedules', __name__)

@api_schedules_bp.route('/api/schedules', methods=['GET'])
def get_schedules():
    """Get list of automated display schedules"""
    return jsonify(load_schedules())

@api_schedules_bp.route('/api/schedules', methods=['POST'])
def add_schedule():
    """Add a new scheduled display change"""
    data = request.json or {}
    name = data.get('name', 'Schedule').strip()
    time_val = data.get('time', '').strip()  # "HH:MM"
    action = data.get('action', 'slideshow')  # "slideshow", "website", "blank", "wake"
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

@api_schedules_bp.route('/api/schedules/<schedule_id>/toggle', methods=['PUT'])
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

@api_schedules_bp.route('/api/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete a schedule"""
    schedules = load_schedules()
    updated = [s for s in schedules if s.get('id') != schedule_id]
    if len(updated) != len(schedules):
        save_schedules(updated)
        return jsonify({"success": True, "schedules": updated})
    return jsonify({"success": False, "error": "Schedule not found"}), 404
