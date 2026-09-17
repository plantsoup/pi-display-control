"""
Browser process and configuration management.
Handles Chromium binary detection, crash preference repair, and process lifecycle.
"""

import os
import sys
import json
import shutil
import subprocess

def get_x_env():
    """Return environment dictionary configured for X11 session"""
    env = os.environ.copy()
    if 'DISPLAY' not in env:
        env['DISPLAY'] = ':0'
    if 'XAUTHORITY' not in env:
        xauth = os.path.expanduser('~/.Xauthority')
        if os.path.exists(xauth):
            env['XAUTHORITY'] = xauth
    return env

def find_chromium():
    """Find installed Chromium binary executable or None if not found"""
    candidates = [
        "/usr/lib/chromium/chromium",
        shutil.which("chromium-browser"),
        shutil.which("chromium"),
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium"
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return shutil.which("chromium-browser") or shutil.which("chromium") or None

def _launch_chromium_process(cmd, env):
    """Launch Chromium process safely, handling environments where Chromium binary is absent"""
    if not cmd or not cmd[0]:
        return None
    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[ERROR] Launching Chromium: {e}", file=sys.stderr)
        return None

def fix_chromium_preferences(user_data_dir):
    """Safely fix Chromium crash bubbles in Preferences JSON"""
    prefs_file = os.path.join(user_data_dir, "Default", "Preferences")
    if not os.path.exists(prefs_file):
        return
    try:
        with open(prefs_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        # Reset exit state
        if data.get("profile", {}).get("exit_type") != "Normal":
            if "profile" not in data:
                data["profile"] = {}
            data["profile"]["exit_type"] = "Normal"
            modified = True
            
        if data.get("profile", {}).get("exited_cleanly") is not True:
            if "profile" not in data:
                data["profile"] = {}
            data["profile"]["exited_cleanly"] = True
            modified = True

        if modified:
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
    except Exception as e:
        # If JSON loading fails due to corruption or formatting, fall back to string replace
        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace('"exited_cleanly":false', '"exited_cleanly":true')
            content = content.replace('"exit_type":"Crashed"', '"exit_type":"Normal"')
            with open(prefs_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            pass

def kill_chromium(target="both"):
    """
    Selectively terminate Chromium instances.
    target: "both" (all chromium), "1" (monitor 1), "2" (monitor 2)
    """
    env = get_x_env()
    try:
        if target == "both":
            subprocess.run(["pkill", "-9", "-f", "chromium"], env=env, stderr=subprocess.DEVNULL)
        elif target == "1":
            subprocess.run(["pkill", "-9", "-f", "chromium-autodarts-monitor1"], env=env, stderr=subprocess.DEVNULL)
        elif target == "2":
            subprocess.run(["pkill", "-9", "-f", "chromium-autodarts-monitor2"], env=env, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[WARN] Error killing Chromium ({target}): {e}", file=sys.stderr)
