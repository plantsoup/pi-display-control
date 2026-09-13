#!/bin/bash

# X display setup
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Kill Chromium first (it might be keeping the displays on)
pkill -9 -f chromium

# Wait a moment for Chromium to fully close
sleep 1

# Try to blank the screens using vcgencmd (Raspberry Pi specific)
# Try with sudo first
sudo vcgencmd display_power 0 2>/dev/null

# Get all connected displays
OUTPUTS=$(xrandr --query | grep " connected" | cut -d' ' -f1)

# Turn off all connected displays using xrandr
for OUTPUT in $OUTPUTS; do
    if [ -n "$OUTPUT" ]; then
        xrandr --output "$OUTPUT" --off
    fi
done

