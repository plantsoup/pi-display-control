#!/bin/bash

# X display setup
export DISPLAY=:0
export XAUTHORITY=/home/gavinspear/.Xauthority

# Turn displays back on using vcgencmd (Raspberry Pi specific)
sudo vcgencmd display_power 1 2>/dev/null || vcgencmd display_power 1 2>/dev/null

# Get all connected displays
OUTPUTS=$(xrandr --query | grep " connected" | cut -d' ' -f1)
OUTPUT_COUNT=$(echo "$OUTPUTS" | wc -l)

# Turn on all connected displays using xrandr
if [ "$OUTPUT_COUNT" -eq 2 ]; then
    # Two monitors
    OUTPUT1=$(echo "$OUTPUTS" | head -n 1)
    OUTPUT2=$(echo "$OUTPUTS" | tail -n 1)
    
    # Get resolutions (look for active mode)
    RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    
    # If no resolution found, try getting the first available mode
    if [ -z "$RES1" ]; then
        RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    fi
    if [ -z "$RES2" ]; then
        RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    fi
    
    # Turn on and configure both monitors
    xrandr --output "$OUTPUT1" --auto --primary --mode "$RES1" --rotate left
    
    # Calculate position for second monitor (after rotation, width = original height)
    MONITOR1_ORIG_WIDTH=$(echo "$RES1" | cut -d'x' -f1)
    MONITOR1_ORIG_HEIGHT=$(echo "$RES1" | cut -d'x' -f2)
    MONITOR1_ROTATED_WIDTH=$MONITOR1_ORIG_HEIGHT
    
    xrandr --output "$OUTPUT2" --auto --mode "$RES2" --pos "${MONITOR1_ROTATED_WIDTH}x0" --rotate left
    sleep 1
elif [ "$OUTPUT_COUNT" -eq 1 ]; then
    # Single monitor
    OUTPUT=$(echo "$OUTPUTS" | head -n 1)
    if [ -n "$OUTPUT" ]; then
        xrandr --output "$OUTPUT" --auto
        # Rotate display left (90 degrees counter-clockwise) to match startup
        xrandr --output "$OUTPUT" --rotate left
        sleep 1
    fi
fi

# Wait a moment for displays to come on
sleep 1

# Now start Chromium using the start.sh script
~/start.sh

