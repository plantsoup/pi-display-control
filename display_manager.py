#!/usr/bin/env python3
"""
Pi Display Manager
Pure Python replacement for legacy display shell scripts.
Manages multi-monitor setup, screen power states, Chromium kiosk instances, and window positioning.
"""

from display import (
    get_x_env,
    find_chromium,
    fix_chromium_preferences,
    kill_chromium,
    get_connected_monitors,
    get_xdotool_windows,
    position_window,
    start_display,
    blank_screen,
    wake_screen,
    toggle_monitor2,
    DEFAULT_AUTODARTS_URL
)

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
