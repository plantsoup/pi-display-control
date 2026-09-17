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
                            params = sch.get("params", {})
                            print(f"[SCHEDULER] Triggering schedule: {sch.get('name', 'Unnamed')} -> {action} at {current_time_str}")
                            trigger_display_action(action, params)

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
