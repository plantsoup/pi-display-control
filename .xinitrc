#!/bin/sh

# xinitrc for Raspberry Pi - Multi-monitor Display & Slideshow Studio
# Supports 1 or 2 monitors with separate Chromium instances
# Designed for headless operation with VNC or local HDMI displays

# Set display environment
export DISPLAY=:0

# Hide mouse cursor when idle
if command -v unclutter >/dev/null 2>&1; then
    unclutter -idle 2 -root &
fi

# Start window manager (optional, but useful for VNC)
# Using openbox for lightweight window management
if command -v openbox >/dev/null 2>&1; then
    openbox &
elif command -v fluxbox >/dev/null 2>&1; then
    fluxbox &
fi

# Wait for network and X to be ready
sleep 3

# Delegate monitor configuration and browser launch to the Python manager
# This ensures consistency with the web UI's "wake" command
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$APP_DIR/display_manager.py" ]; then
    python3 "$APP_DIR/display_manager.py" wake
elif [ -f "$HOME/apps/pi-display-control/display_manager.py" ]; then
    python3 "$HOME/apps/pi-display-control/display_manager.py" wake
elif [ -f "$HOME/pi-display-control/display_manager.py" ]; then
    python3 "$HOME/pi-display-control/display_manager.py" wake
else
    # Fallback to current directory
    python3 display_manager.py wake
fi

# Keep the session running
wait
