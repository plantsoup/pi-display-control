#!/bin/bash

# X display setup
export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Default sites (can be overridden by arguments)
# Argument patterns:
#   Monitor 1 only: [url1]
#   Monitor 2 only: ['', url2]
#   Both monitors: [url1, url2]
DEFAULT_SITE="https://spot.spear.ac"

# Parse arguments
ARG1="${1:-}"
ARG2="${2:-}"

# Determine which monitors to use and their URLs
if [ -n "$ARG1" ] && [ -n "$ARG2" ]; then
    # Both monitors: [url1, url2]
    SITE1="$ARG1"
    SITE2="$ARG2"
    USE_MONITOR1=true
    USE_MONITOR2=true
elif [ -z "$ARG1" ] && [ -n "$ARG2" ]; then
    # Monitor 2 only: ['', url2]
    SITE1="$DEFAULT_SITE"  # Not used, but set for safety
    SITE2="$ARG2"
    USE_MONITOR1=false
    USE_MONITOR2=true
elif [ -n "$ARG1" ] && [ -z "$ARG2" ]; then
    # Monitor 1 only: [url1]
    SITE1="$ARG1"
    SITE2="$DEFAULT_SITE"  # Not used, but set for safety
    USE_MONITOR1=true
    USE_MONITOR2=false
else
    # No arguments: use defaults for both
    SITE1="$DEFAULT_SITE"
    SITE2="$DEFAULT_SITE"
    USE_MONITOR1=true
    USE_MONITOR2=true
fi

# Selectively kill existing Chromium instance(s)
if [ "$USE_MONITOR1" = true ] && [ "$USE_MONITOR2" = true ]; then
    pkill -9 -f chromium
elif [ "$USE_MONITOR1" = true ]; then
    pkill -9 -f "chromium-autodarts-monitor1"
elif [ "$USE_MONITOR2" = true ]; then
    pkill -9 -f "chromium-autodarts-monitor2"
fi

# Fix Chromium crash state for user data directories
PREFS1="$HOME/.config/chromium-autodarts-monitor1/Default/Preferences"
PREFS2="$HOME/.config/chromium-autodarts-monitor2/Default/Preferences"
PREFS_SINGLE="$HOME/.config/chromium-autodarts/Default/Preferences"
PREFS_DEFAULT="$HOME/.config/chromium/Default/Preferences"

[ -f "$PREFS1" ] && sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS1" 2>/dev/null
[ -f "$PREFS1" ] && sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PREFS1" 2>/dev/null
[ -f "$PREFS2" ] && sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS2" 2>/dev/null
[ -f "$PREFS2" ] && sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PREFS2" 2>/dev/null
[ -f "$PREFS_SINGLE" ] && sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS_SINGLE" 2>/dev/null
[ -f "$PREFS_SINGLE" ] && sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PREFS_SINGLE" 2>/dev/null
[ -f "$PREFS_DEFAULT" ] && sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS_DEFAULT" 2>/dev/null
[ -f "$PREFS_DEFAULT" ] && sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PREFS_DEFAULT" 2>/dev/null

# Detect number of connected monitors
OUTPUTS=$(xrandr --query 2>/dev/null | grep " connected" | cut -d' ' -f1)
OUTPUT_COUNT=$(echo "$OUTPUTS" | wc -l | tr -d ' ')

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

if [ "$OUTPUT_COUNT" -eq 2 ]; then
    # Two monitors - launch separate Chromium instances
    OUTPUT1=$(echo "$OUTPUTS" | head -n 1)
    OUTPUT2=$(echo "$OUTPUTS" | tail -n 1)
    
    # Ensure OUTPUT1 is set as primary (this helps with window placement)
    xrandr --output "$OUTPUT1" --primary 2>/dev/null
    
    # Launch monitor 1 if requested
    if [ "$USE_MONITOR1" = true ]; then
    
    # Get monitor resolutions (look for active mode with *)
    RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    
    # If no resolution found, try getting the first available mode
    if [ -z "$RES1" ]; then
        RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    fi
    if [ -z "$RES2" ]; then
        RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
    fi
    
    # Get monitor positions from xrandr (look for "connected primary 1920x1080+0+0" format)
    POS1=$(xrandr --query | grep "^$OUTPUT1" | grep -oE '\+[0-9]+\+[0-9]+' | head -n 1)
    POS2=$(xrandr --query | grep "^$OUTPUT2" | grep -oE '\+[0-9]+\+[0-9]+' | head -n 1)
    
    # Extract coordinates (format: +X+Y)
    X1=$(echo "$POS1" | sed 's/^+\([0-9]*\)+.*/\1/')
    Y1=$(echo "$POS1" | sed 's/^+[0-9]*+\([0-9]*\)/\1/')
    X2=$(echo "$POS2" | sed 's/^+\([0-9]*\)+.*/\1/')
    Y2=$(echo "$POS2" | sed 's/^+[0-9]*+\([0-9]*\)/\1/')
    
    # If positions not found, calculate them
    if [ -z "$X1" ] || [ -z "$Y1" ]; then
        X1=0
        Y1=0
    fi
    if [ -z "$X2" ] || [ -z "$Y2" ]; then
        # Calculate position based on first monitor's dimensions
        # First get the rotation to determine actual width
        ROT1_TEMP=$(xrandr --query | grep "^$OUTPUT1" | grep -oE '\s+(left|right|normal|inverted)\s+' | head -n 1 | tr -d ' ')
        if [ -z "$ROT1_TEMP" ]; then
            ROT1_TEMP=$(xrandr --query | grep -A 1 "^$OUTPUT1" | grep -E '\s+(left|right|normal|inverted)' | head -n 1 | grep -oE '(left|right|normal|inverted)' | head -n 1)
        fi
        ROT1_TEMP="${ROT1_TEMP:-normal}"
        
        MONITOR1_ORIG_WIDTH=$(echo "$RES1" | cut -d'x' -f1)
        MONITOR1_ORIG_HEIGHT=$(echo "$RES1" | cut -d'x' -f2)
        
        # After left rotation: width = original height
        if [ "$ROT1_TEMP" = "left" ] || [ "$ROT1_TEMP" = "right" ]; then
            MONITOR1_WIDTH=$MONITOR1_ORIG_HEIGHT
        else
            MONITOR1_WIDTH=$MONITOR1_ORIG_WIDTH
        fi
        X2=$MONITOR1_WIDTH
        Y2=0
    fi
    
    # Get rotation to determine actual dimensions
    # Get the current rotation from the active line (the one with the resolution and position)
    ROT1=$(xrandr --query | grep "^$OUTPUT1" | grep -oE '\s+(left|right|normal|inverted)\s+' | head -n 1 | tr -d ' ')
    ROT2=$(xrandr --query | grep "^$OUTPUT2" | grep -oE '\s+(left|right|normal|inverted)\s+' | head -n 1 | tr -d ' ')
    
    # If not found in the main line, check if it's in the mode line
    if [ -z "$ROT1" ]; then
        ROT1=$(xrandr --query | grep -A 1 "^$OUTPUT1" | grep -E '\s+(left|right|normal|inverted)' | head -n 1 | grep -oE '(left|right|normal|inverted)' | head -n 1)
    fi
    if [ -z "$ROT2" ]; then
        ROT2=$(xrandr --query | grep -A 1 "^$OUTPUT2" | grep -E '\s+(left|right|normal|inverted)' | head -n 1 | grep -oE '(left|right|normal|inverted)' | head -n 1)
    fi
    
    # Default to normal if still not found
    ROT1="${ROT1:-normal}"
    ROT2="${ROT2:-normal}"
    
    MONITOR1_ORIG_WIDTH=$(echo "$RES1" | cut -d'x' -f1)
    MONITOR1_ORIG_HEIGHT=$(echo "$RES1" | cut -d'x' -f2)
    MONITOR2_ORIG_WIDTH=$(echo "$RES2" | cut -d'x' -f1)
    MONITOR2_ORIG_HEIGHT=$(echo "$RES2" | cut -d'x' -f2)
    
    # Calculate dimensions after rotation
    if [ "$ROT1" = "left" ] || [ "$ROT1" = "right" ]; then
        MONITOR1_WIDTH=$MONITOR1_ORIG_HEIGHT
        MONITOR1_HEIGHT=$MONITOR1_ORIG_WIDTH
    else
        MONITOR1_WIDTH=$MONITOR1_ORIG_WIDTH
        MONITOR1_HEIGHT=$MONITOR1_ORIG_HEIGHT
    fi
    
    if [ "$ROT2" = "left" ] || [ "$ROT2" = "right" ]; then
        MONITOR2_WIDTH=$MONITOR2_ORIG_HEIGHT
        MONITOR2_HEIGHT=$MONITOR2_ORIG_WIDTH
    else
        MONITOR2_WIDTH=$MONITOR2_ORIG_WIDTH
        MONITOR2_HEIGHT=$MONITOR2_ORIG_HEIGHT
    fi
    
        # Launch Chromium on monitor 1
        USER_DATA_DIR1="$HOME/.config/chromium-autodarts-monitor1"
        mkdir -p "$USER_DATA_DIR1"
        
        # Get list of existing Chromium windows before launching
        if command -v xdotool >/dev/null 2>&1; then
            EXISTING_WINDOWS=$(xdotool search --class chromium 2>/dev/null)
        else
            EXISTING_WINDOWS=""
        fi
        
        # Launch first Chromium instance
        $CHROMIUM_CMD \
            --kiosk \
            --disable-session-crashed-bubble \
            --disable-breakpad \
            --user-data-dir="$USER_DATA_DIR1" \
            "$SITE1" \
            &> /tmp/chromium-monitor1.log &
        
        CHROMIUM_PID1=$!
        
        # Wait for first window to appear, then move it
        sleep 4
        
        if command -v xdotool >/dev/null 2>&1; then
            # Find the new window (one that wasn't in the existing list)
            ALL_WINDOWS=$(xdotool search --class chromium 2>/dev/null)
            for WINDOW_ID in $ALL_WINDOWS; do
                if ! echo "$EXISTING_WINDOWS" | grep -q "^$WINDOW_ID$"; then
                    # This is the new window for monitor 1
                    xdotool windowmove $WINDOW_ID $X1 $Y1 2>/dev/null
                    xdotool windowsize $WINDOW_ID $MONITOR1_WIDTH $MONITOR1_HEIGHT 2>/dev/null
                    break
                fi
            done
        fi
    fi
    
    # Launch monitor 2 if requested
    if [ "$USE_MONITOR2" = true ]; then
        # Launch Chromium on monitor 2
        USER_DATA_DIR2="$HOME/.config/chromium-autodarts-monitor2"
        mkdir -p "$USER_DATA_DIR2"
        
        # Get updated list of windows before launching second instance
        if command -v xdotool >/dev/null 2>&1; then
            EXISTING_WINDOWS=$(xdotool search --class chromium 2>/dev/null)
        fi
        
        # Launch second instance
        $CHROMIUM_CMD \
            --kiosk \
            --disable-session-crashed-bubble \
            --disable-breakpad \
            --user-data-dir="$USER_DATA_DIR2" \
            "$SITE2" \
            &> /tmp/chromium-monitor2.log &
        
        CHROMIUM_PID2=$!
        
        # Wait for second window to appear, then move it
        sleep 4
        
        if command -v xdotool >/dev/null 2>&1; then
            # Find the new window (one that wasn't in the existing list)
            ALL_WINDOWS=$(xdotool search --class chromium 2>/dev/null)
            for WINDOW_ID in $ALL_WINDOWS; do
                if ! echo "$EXISTING_WINDOWS" | grep -q "^$WINDOW_ID$"; then
                    # This is the new window for monitor 2
                    xdotool windowmove $WINDOW_ID $X2 $Y2 2>/dev/null
                    xdotool windowsize $WINDOW_ID $MONITOR2_WIDTH $MONITOR2_HEIGHT 2>/dev/null
                    break
                fi
            done
        else
            echo "xdotool not found - windows may not be positioned correctly" >&2
            echo "Install xdotool for proper multi-monitor support: sudo apt-get install xdotool" >&2
        fi
    fi
else
    # Single monitor - determine which site to use based on arguments
    if [ "$USE_MONITOR2" = true ] && [ "$USE_MONITOR1" = false ]; then
        # User wants monitor 2 only, but only one monitor is connected
        # Use monitor 2's site
        SINGLE_SITE="$SITE2"
        USER_DATA_DIR="$HOME/.config/chromium-autodarts-monitor2"
    else
        # Use monitor 1's site (default)
        SINGLE_SITE="$SITE1"
        USER_DATA_DIR="$HOME/.config/chromium-autodarts"
    fi
    
    mkdir -p "$USER_DATA_DIR"
    
    # Ensure preferences file exists and is fixed
    PREFS_SINGLE="$USER_DATA_DIR/Default/Preferences"
    if [ -f "$PREFS_SINGLE" ]; then
        sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS_SINGLE" 2>/dev/null
        sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$PREFS_SINGLE" 2>/dev/null
    fi
    
    # Launch Chromium in kiosk mode for single monitor
    $CHROMIUM_CMD \
        --kiosk \
        --disable-session-crashed-bubble \
        --disable-breakpad \
        --user-data-dir="$USER_DATA_DIR" \
        "$SINGLE_SITE" \
        &> /dev/null &
fi
