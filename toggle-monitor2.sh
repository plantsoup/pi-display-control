#!/bin/bash

# Simple toggle script for monitor 2 rotation (vertical/horizontal)
# Usage: ./toggle-monitor2.sh [restart]
#   - If "restart" is provided, will also restart Chromium on monitor 2

# X display setup
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Get all connected displays
OUTPUTS=$(xrandr --query 2>/dev/null | grep " connected" | cut -d' ' -f1)
OUTPUT_COUNT=$(echo "$OUTPUTS" | wc -l | tr -d ' ')

if [ "$OUTPUT_COUNT" -lt 2 ]; then
    echo "Error: Need 2 monitors connected" >&2
    exit 1
fi

# Get the second monitor
OUTPUT2=$(echo "$OUTPUTS" | tail -n 1)
OUTPUT1=$(echo "$OUTPUTS" | head -n 1)

# Get current rotation of monitor 2
CURRENT_ROT=$(xrandr --query | grep "^$OUTPUT2" | grep -oE '\s+(left|right|normal|inverted)\s+' | head -n 1 | tr -d ' ')

# If not found, try alternative method
if [ -z "$CURRENT_ROT" ]; then
    CURRENT_ROT=$(xrandr --query | grep -A 1 "^$OUTPUT2" | grep -E '\s+(left|right|normal|inverted)' | head -n 1 | grep -oE '(left|right|normal|inverted)' | head -n 1)
fi

# Default to normal if not found
CURRENT_ROT="${CURRENT_ROT:-normal}"

# Get current resolution
RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
if [ -z "$RES2" ]; then
    RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
fi

# Get current position
POS2=$(xrandr --query | grep "^$OUTPUT2" | grep -oE '\+[0-9]+\+[0-9]+' | head -n 1)
X2=$(echo "$POS2" | sed 's/^+\([0-9]*\)+.*/\1/')
Y2=$(echo "$POS2" | sed 's/^+[0-9]*+\([0-9]*\)/\1/')

# If position not found, calculate it
if [ -z "$X2" ] || [ -z "$Y2" ]; then
    # Get monitor 1 dimensions to calculate position
    RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    if [ -z "$RES1" ]; then
        RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    fi
    
    ROT1=$(xrandr --query | grep "^$OUTPUT1" | grep -oE '\s+(left|right|normal|inverted)\s+' | head -n 1 | tr -d ' ')
    if [ -z "$ROT1" ]; then
        ROT1=$(xrandr --query | grep -A 1 "^$OUTPUT1" | grep -E '\s+(left|right|normal|inverted)' | head -n 1 | grep -oE '(left|right|normal|inverted)' | head -n 1)
    fi
    ROT1="${ROT1:-normal}"
    
    MONITOR1_ORIG_WIDTH=$(echo "$RES1" | cut -d'x' -f1)
    MONITOR1_ORIG_HEIGHT=$(echo "$RES1" | cut -d'x' -f2)
    
    if [ "$ROT1" = "left" ] || [ "$ROT1" = "right" ]; then
        MONITOR1_WIDTH=$MONITOR1_ORIG_HEIGHT
    else
        MONITOR1_WIDTH=$MONITOR1_ORIG_WIDTH
    fi
    X2=$MONITOR1_WIDTH
    Y2=0
fi

# Toggle rotation
if [ "$CURRENT_ROT" = "left" ] || [ "$CURRENT_ROT" = "right" ]; then
    # Currently vertical, switch to horizontal (normal)
    NEW_ROT="normal"
    echo "Switching monitor 2 ($OUTPUT2) from vertical to horizontal..."
else
    # Currently horizontal, switch to vertical (left)
    NEW_ROT="left"
    echo "Switching monitor 2 ($OUTPUT2) from horizontal to vertical..."
fi

# Apply new rotation
xrandr --output "$OUTPUT2" --rotate "$NEW_ROT"
sleep 1

# Restart Chromium if requested
if [ "$1" = "restart" ]; then
    echo "Restarting Chromium on monitor 2..."
    
    # Kill Chromium instance for monitor 2
    pkill -9 -f "chromium-autodarts-monitor2"
    sleep 1
    
    # Get new dimensions after rotation
    MONITOR2_ORIG_WIDTH=$(echo "$RES2" | cut -d'x' -f1)
    MONITOR2_ORIG_HEIGHT=$(echo "$RES2" | cut -d'x' -f2)
    
    if [ "$NEW_ROT" = "left" ] || [ "$NEW_ROT" = "right" ]; then
        MONITOR2_WIDTH=$MONITOR2_ORIG_HEIGHT
        MONITOR2_HEIGHT=$MONITOR2_ORIG_WIDTH
    else
        MONITOR2_WIDTH=$MONITOR2_ORIG_WIDTH
        MONITOR2_HEIGHT=$MONITOR2_ORIG_HEIGHT
    fi
    
    # Find Chromium executable
    if [ -f "/usr/lib/chromium/chromium" ]; then
        CHROMIUM_CMD="/usr/lib/chromium/chromium"
    elif command -v chromium-browser >/dev/null 2>&1; then
        CHROMIUM_CMD="chromium-browser"
    elif command -v chromium >/dev/null 2>&1; then
        CHROMIUM_CMD="chromium"
    else
        echo "Chromium not found!" >&2
        exit 1
    fi
    
    USER_DATA_DIR2="$HOME/.config/chromium-autodarts-monitor2"
    
    # Get site from start.sh default or use default
    SITE2="${2:-https://play.autodarts.io/boards/62f17919-bbb2-443b-bf0e-a5d6e27c7898/follow}"
    
    # Launch Chromium on monitor 2
    $CHROMIUM_CMD \
        --kiosk \
        --disable-session-crashed-bubble \
        --disable-breakpad \
        --user-data-dir="$USER_DATA_DIR2" \
        "$SITE2" \
        &> /dev/null &
    
    # Wait for window to appear, then position it
    sleep 3
    
    if command -v xdotool >/dev/null 2>&1; then
        EXISTING_WINDOWS=$(xdotool search --class chromium 2>/dev/null)
        sleep 1
        ALL_WINDOWS=$(xdotool search --class chromium 2>/dev/null)
        for WINDOW_ID in $ALL_WINDOWS; do
            if ! echo "$EXISTING_WINDOWS" | grep -q "^$WINDOW_ID$"; then
                # This is the new window for monitor 2
                xdotool windowmove $WINDOW_ID $X2 $Y2 2>/dev/null
                xdotool windowsize $WINDOW_ID $MONITOR2_WIDTH $MONITOR2_HEIGHT 2>/dev/null
                break
            fi
        done
    fi
    
    echo "Chromium restarted on monitor 2"
fi

echo "Done! Monitor 2 is now $NEW_ROT"



