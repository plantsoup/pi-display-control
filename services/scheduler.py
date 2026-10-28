"""
Background scheduler service.
Evaluates time-based trigger rules and dispatches actions to the display service.
"""

import sys
import time
import threading
from datetime import datetime
from .storage import load_schedules
from .display_service import trigger_display_action

last_triggered_minute = ""
_scheduler_thread = None
_scheduler_lock = threading.Lock()

def scheduler_worker():
    """Background worker that executes scheduled time events"""
    global last_triggered_minute
    while True:
        try:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")  # "14:30"
            current_day_str = now.strftime("%a").lower()  # "mon", "tue", etc.

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
                            params = dict(sch.get("params", {}) or {})
                            target_node = params.get("target_node", "local") or "local"
                            print(f"[SCHEDULER] Triggering schedule: {sch.get('name', 'Unnamed')} -> {action} (target={target_node}) at {current_time_str}")
                            if target_node == "local":
                                trigger_display_action(action, params)
                            else:
                                from .nodes_service import dispatch_to_node, broadcast_to_nodes
                                sched_action = action if action in ("blank", "wake") else "display"
                                sched_payload = dict(params)
                                if action == "slideshow":
                                    sched_payload["mode"] = "slideshow"
                                    sched_payload["slideshow_mode"] = params.get("mode", "random")
                                    sched_payload.setdefault("stream_from_main", True)
                                elif action == "website":
                                    sched_payload["mode"] = "website"
                                if target_node == "all":
                                    broadcast_to_nodes(action=sched_action, payload=sched_payload, include_local=True)
                                else:
                                    dispatch_to_node(target_node, action=sched_action, payload=sched_payload)

                last_triggered_minute = minute_key
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}", file=sys.stderr)

        time.sleep(15)

def start_scheduler_thread():
    """Start background scheduler daemon thread if not already running"""
    global _scheduler_thread
    with _scheduler_lock:
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True, name="PiSchedulerThread")
            _scheduler_thread.start()
    return _scheduler_thread
