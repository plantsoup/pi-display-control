#!/usr/bin/env python3
"""
Pi Display Manager
Pure Python replacement for legacy display shell scripts (start.sh, blank-screen.sh, wake-screen.sh, toggle-monitor2.sh).
Manages multi-monitor setup, screen power states, Chromium kiosk instances, and window positioning.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import re
from pathlib import Path

# Default site configuration
DEFAULT_AUTODARTS_URL = "https://play.autodarts.io/boards/64a51258-5e52-4a97-9311-9cb81bd7e355/follow"

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

def get_connected_monitors():
    """
    Query xrandr for connected outputs and their configurations.
    Returns list of monitor dictionaries.
    """
    env = get_x_env()
    try:
        res = subprocess.run(["xrandr", "--query"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        output = res.stdout
    except Exception:
        return []

    monitors = []
    current_monitor = None

    for line in output.splitlines():
        if " connected" in line:
            parts = line.split()
            name = parts[0]
            is_primary = "primary" in parts
            
            # Match resolution and position e.g. 1920x1080+0+0
            res_pos_match = re.search(r'(\d+)x(\d+)\+(\d+)\+(\d+)', line)
            
            # Match rotation
            rot_match = re.search(r'\s+(left|right|inverted)\s+', line)
            rotation = rot_match.group(1) if rot_match else "normal"

            orig_w, orig_h = 1920, 1080
            pos_x, pos_y = 0, 0
            if res_pos_match:
                orig_w = int(res_pos_match.group(1))
                orig_h = int(res_pos_match.group(2))
                pos_x = int(res_pos_match.group(3))
                pos_y = int(res_pos_match.group(4))

            # Calculate dimensions after rotation
            if rotation in ['left', 'right']:
                width = orig_h
                height = orig_w
            else:
                width = orig_w
                height = orig_h

            current_monitor = {
                "name": name,
                "primary": is_primary,
                "orig_width": orig_w,
                "orig_height": orig_h,
                "width": width,
                "height": height,
                "pos_x": pos_x,
                "pos_y": pos_y,
                "rotation": rotation,
                "modes": []
            }
            monitors.append(current_monitor)
        elif current_monitor and re.match(r'^\s+(\d+x\d+)', line):
            mode_match = re.match(r'^\s+(\d+x\d+)', line)
            if mode_match:
                current_monitor["modes"].append(mode_match.group(1))

    return monitors

def get_xdotool_windows():
    """Retrieve list of existing Chromium window IDs"""
    env = get_x_env()
    if not shutil.which("xdotool"):
        return []
    try:
        res = subprocess.run(["xdotool", "search", "--class", "chromium"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return [w.strip() for w in res.stdout.strip().splitlines() if w.strip()]
    except Exception:
        pass
    return []

def position_window(existing_windows, x, y, width, height, max_attempts=8):
    """Wait for new Chromium window and position/resize it with xdotool"""
    env = get_x_env()
    if not shutil.which("xdotool"):
        return False

    existing_set = set(existing_windows)
    for _ in range(max_attempts):
        time.sleep(0.5)
        current = get_xdotool_windows()
        new_windows = [w for w in current if w not in existing_set]
        if new_windows:
            target_id = new_windows[0]
            try:
                subprocess.run(["xdotool", "windowmove", target_id, str(x), str(y)], env=env, stderr=subprocess.DEVNULL)
                subprocess.run(["xdotool", "windowsize", target_id, str(width), str(height)], env=env, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    return False

def start_display(url1="", url2="", monitor="both"):
    """
    Launch Chromium kiosk display for monitor 1, monitor 2, or both.
    """
    env = get_x_env()
    chromium_cmd = find_chromium()
    home_dir = os.path.expanduser("~")

    # Determine URLs
    site1 = url1 if url1 else DEFAULT_AUTODARTS_URL
    site2 = url2 if url2 else (url1 if url1 else DEFAULT_AUTODARTS_URL)

    use_m1 = monitor in ["1", "both"]
    use_m2 = monitor in ["2", "both"]

    # Selectively terminate previous instances
    kill_chromium(monitor)

    # Preferences directories
    user_data_m1 = os.path.join(home_dir, ".config", "chromium-autodarts-monitor1")
    user_data_m2 = os.path.join(home_dir, ".config", "chromium-autodarts-monitor2")
    user_data_single = os.path.join(home_dir, ".config", "chromium-autodarts")
    user_data_default = os.path.join(home_dir, ".config", "chromium")

    for d in [user_data_m1, user_data_m2, user_data_single, user_data_default]:
        fix_chromium_preferences(d)

    monitors = get_connected_monitors()

    if len(monitors) >= 2:
        m1 = monitors[0]
        m2 = monitors[1]

        # Ensure primary output is set
        subprocess.run(["xrandr", "--output", m1["name"], "--primary"], env=env, stderr=subprocess.DEVNULL)

        # Monitor 2 position calculation if needed
        pos_x2 = m2["pos_x"]
        pos_y2 = m2["pos_y"]
        if pos_x2 == 0 and pos_y2 == 0 and m1["width"] > 0:
            pos_x2 = m1["width"]

        # Launch Monitor 1
        if use_m1:
            os.makedirs(user_data_m1, exist_ok=True)
            existing_win = get_xdotool_windows()
            cmd1 = [
                chromium_cmd,
                "--kiosk",
                "--disable-session-crashed-bubble",
                "--disable-breakpad",
                f"--user-data-dir={user_data_m1}",
                site1
            ]
            _launch_chromium_process(cmd1, env)
            if existing_win:
                position_window(existing_win, m1["pos_x"], m1["pos_y"], m1["width"], m1["height"])

        # Launch Monitor 2
        if use_m2:
            os.makedirs(user_data_m2, exist_ok=True)
            existing_win = get_xdotool_windows()
            cmd2 = [
                chromium_cmd,
                "--kiosk",
                "--disable-session-crashed-bubble",
                "--disable-breakpad",
                f"--user-data-dir={user_data_m2}",
                site2
            ]
            _launch_chromium_process(cmd2, env)
            if existing_win:
                position_window(existing_win, pos_x2, pos_y2, m2["width"], m2["height"])

    else:
        # Single monitor
        target_site = site2 if (use_m2 and not use_m1) else site1
        target_dir = user_data_m2 if (use_m2 and not use_m1) else user_data_single
        os.makedirs(target_dir, exist_ok=True)
        fix_chromium_preferences(target_dir)

        cmd = [
            chromium_cmd,
            "--kiosk",
            "--disable-session-crashed-bubble",
            "--disable-breakpad",
            f"--user-data-dir={target_dir}",
            target_site
        ]
        _launch_chromium_process(cmd, env)

    return True, "Display started successfully"

def _set_display_power(power_on=True):
    """Attempt hardware display power control via vcgencmd without blocking on sudo password"""
    val = "1" if power_on else "0"
    vcgen = shutil.which("vcgencmd") or ("/usr/bin/vcgencmd" if os.path.exists("/usr/bin/vcgencmd") else None)
    if not vcgen:
        return
    env = get_x_env()
    try:
        subprocess.run(["sudo", "-n", vcgen, "display_power", val], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    try:
        subprocess.run([vcgen, "display_power", val], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def blank_screen():
    """Power off screens and terminate Chromium"""
    env = get_x_env()

    # Kill Chromium
    kill_chromium("both")

    # Raspberry Pi hardware blanking
    _set_display_power(power_on=False)

    # Turn off outputs via xrandr
    if shutil.which("xrandr"):
        monitors = get_connected_monitors()
        for m in monitors:
            subprocess.run(["xrandr", "--output", m["name"], "--off"], env=env, stderr=subprocess.DEVNULL)

    return True, "Display blanked successfully"

def wake_screen(url1="", url2=""):
    """Power on screens, restore display configuration and restart Chromium"""
    env = get_x_env()

    # Hardware power on
    _set_display_power(power_on=True)

    # Restore xrandr outputs
    if shutil.which("xrandr"):
        monitors = get_connected_monitors()
        if len(monitors) >= 2:
            m1 = monitors[0]
            m2 = monitors[1]
            mode1 = m1["modes"][0] if m1.get("modes") else f"{m1['orig_width']}x{m1['orig_height']}"
            mode2 = m2["modes"][0] if m2.get("modes") else f"{m2['orig_width']}x{m2['orig_height']}"

            # Re-enable primary monitor rotated left
            subprocess.run(["xrandr", "--output", m1["name"], "--auto", "--primary", "--mode", mode1, "--rotate", "left"], env=env, stderr=subprocess.DEVNULL)
            
            # Second monitor rotated right / placed side by side
            rot_w1 = m1["orig_height"] if m1["orig_height"] > 0 else 1080
            subprocess.run(["xrandr", "--output", m2["name"], "--auto", "--mode", mode2, "--pos", f"{rot_w1}x0", "--rotate", "right"], env=env, stderr=subprocess.DEVNULL)
        elif len(monitors) == 1:
            m = monitors[0]
            subprocess.run(["xrandr", "--output", m["name"], "--auto", "--rotate", "left"], env=env, stderr=subprocess.DEVNULL)

    return start_display(url1=url1, url2=url2, monitor="both")

def toggle_monitor2(restart_chromium=False, site=None):
    """Toggle monitor 2 between vertical (left) and horizontal (normal) orientation"""
    env = get_x_env()
    monitors = get_connected_monitors()
    if len(monitors) < 2:
        return False, "Need at least 2 connected monitors"

    m1 = monitors[0]
    m2 = monitors[1]

    new_rotation = "normal" if m2["rotation"] in ["left", "right"] else "left"
    subprocess.run(["xrandr", "--output", m2["name"], "--rotate", new_rotation], env=env, stderr=subprocess.DEVNULL)
    time.sleep(1)

    if restart_chromium:
        kill_chromium("2")
        time.sleep(1)
        target_site = site if site else DEFAULT_AUTODARTS_URL
        start_display(url2=target_site, monitor="2")

    return True, f"Monitor 2 rotation toggled to {new_rotation}"

# ----------------------------------------------------------------------
# Command-Line Interface (CLI) Entrypoint
# ----------------------------------------------------------------------
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Pi Display Control CLI")
    subparsers = parser.add_subparsers(dest="action", help="Action to execute")

    # start command
    start_parser = subparsers.add_parser("start", help="Start or update display")
    start_parser.add_argument("url1", nargs="?", default="", help="URL for Monitor 1")
    start_parser.add_argument("url2", nargs="?", default="", help="URL for Monitor 2")
    start_parser.add_argument("--monitor", choices=["1", "2", "both"], default="both", help="Target monitor")

    # blank command
    subparsers.add_parser("blank", help="Blank/power off display screens")

    # wake command
    wake_parser = subparsers.add_parser("wake", help="Wake/power on display screens")
    wake_parser.add_argument("url1", nargs="?", default="", help="URL for Monitor 1")
    wake_parser.add_argument("url2", nargs="?", default="", help="URL for Monitor 2")

    # toggle command
    toggle_parser = subparsers.add_parser("toggle-monitor2", help="Toggle monitor 2 vertical/horizontal orientation")
    toggle_parser.add_argument("--restart", action="store_true", help="Restart Chromium on monitor 2")
    toggle_parser.add_argument("--url", default="", help="URL for monitor 2 if restarting")

    # status command
    subparsers.add_parser("status", help="Show connected monitor status")

    args = parser.parse_args()

    if args.action == "start":
        success, msg = start_display(url1=args.url1, url2=args.url2, monitor=args.monitor)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "blank":
        success, msg = blank_screen()
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "wake":
        success, msg = wake_screen(url1=args.url1, url2=args.url2)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "toggle-monitor2":
        success, msg = toggle_monitor2(restart_chromium=args.restart, site=args.url)
        print(f"[{'OK' if success else 'ERROR'}] {msg}")
    elif args.action == "status":
        monitors = get_connected_monitors()
        print(f"Found {len(monitors)} connected monitors:")
        for idx, m in enumerate(monitors, 1):
            print(f"  Monitor {idx} ({m['name']}): {m['width']}x{m['height']} (rotation: {m['rotation']}, pos: +{m['pos_x']}+{m['pos_y']})")
    else:
        parser.print_help()
