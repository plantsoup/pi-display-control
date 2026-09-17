"""
Screen power management, blanking, waking, and monitor orientation controls.
"""

import os
import time
import shutil
import subprocess
from .browser import get_x_env, kill_chromium
from .monitors import get_connected_monitors
from .manager import start_display, DEFAULT_AUTODARTS_URL

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
