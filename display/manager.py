"""
Display launcher and orchestration engine.
Coordinates Chromium instances across single and multi-monitor setups.
"""

import os
import subprocess
from .browser import get_x_env, find_chromium, kill_chromium, fix_chromium_preferences, _launch_chromium_process
from .monitors import get_connected_monitors
from .window import get_xdotool_windows, position_window
from .config import (
    DEFAULT_AUTODARTS_URL,
    DEFAULT_AUTODARTS_URL2,
    resolve_monitor_default_url
)

def start_display(url1="", url2="", monitor="both"):
    """
    Launch Chromium kiosk display for monitor 1, monitor 2, or both.
    Uses configured default site/wallpaper when URLs are omitted.
    """
    env = get_x_env()
    chromium_cmd = find_chromium()
    home_dir = os.path.expanduser("~")

    # Determine URLs using configured persistent default site/wallpaper if not specified
    default_url1 = resolve_monitor_default_url("1")
    default_url2 = resolve_monitor_default_url("2")

    site1 = url1 if url1 else default_url1
    site2 = url2 if url2 else (url1 if url1 else default_url2)

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
