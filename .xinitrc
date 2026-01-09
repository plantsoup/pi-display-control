
#!/bin/sh

# xinitrc for Raspberry Pi - Display play.autodarts.io
# Supports 1 or 2 monitors with separate Chromium instances
# Designed for headless operation with VNC

# Set display environment
export DISPLAY=:0

# Start window manager (optional, but useful for VNC)
# Using openbox for lightweight window management
if command -v openbox >/dev/null 2>&1; then
    openbox &
elif command -v fluxbox >/dev/null 2>&1; then
    fluxbox &
fi

# Wait for network to be ready
sleep 3

# Detect connected monitors and configure them
if command -v xrandr >/dev/null 2>&1; then
    # Get all connected displays
    OUTPUTS=$(xrandr --query | grep " connected" | cut -d' ' -f1)
    OUTPUT_COUNT=$(echo "$OUTPUTS" | wc -l)
    
    if [ "$OUTPUT_COUNT" -eq 2 ]; then
        # Two monitors detected - configure as separate displays (not extended)
        OUTPUT1=$(echo "$OUTPUTS" | head -n 1)
        OUTPUT2=$(echo "$OUTPUTS" | tail -n 1)
        
        # Get preferred/current resolutions for both outputs (look for * indicating active mode)
        RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
        RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "^\s+[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
        
        # If no resolution found, try getting the first available mode
        if [ -z "$RES1" ]; then
            RES1=$(xrandr --query | grep -A 10 "^$OUTPUT1" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
        fi
        if [ -z "$RES2" ]; then
            RES2=$(xrandr --query | grep -A 10 "^$OUTPUT2" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}')
        fi
        
        # Configure both monitors as separate (side-by-side, not extended)
        # Set OUTPUT1 as primary at position 0,0, rotated left
        xrandr --output "$OUTPUT1" --primary --mode "$RES1" --pos 0x0 --rotate left
        
        # Get the height of OUTPUT1 after rotation (width becomes height when rotated)
        # When rotated left, width and height swap
        MONITOR1_ORIG_WIDTH=$(echo "$RES1" | cut -d'x' -f1)
        MONITOR1_ORIG_HEIGHT=$(echo "$RES1" | cut -d'x' -f2)
        # After left rotation: new width = original height, new height = original width
        MONITOR1_ROTATED_WIDTH=$MONITOR1_ORIG_HEIGHT
        
        # Set OUTPUT2 at position to the right of OUTPUT1, rotated left
        xrandr --output "$OUTPUT2" --mode "$RES2" --pos "${MONITOR1_ROTATED_WIDTH}x0" --rotate left
        
        sleep 2
        
        # Launch Chromium instances on each monitor
        if command -v chromium-browser >/dev/null 2>&1; then
            CHROMIUM_CMD="chromium-browser"
        elif command -v chromium >/dev/null 2>&1; then
            CHROMIUM_CMD="chromium"
        else
            CHROMIUM_CMD=""
        fi
        
        if [ -n "$CHROMIUM_CMD" ]; then
            # Get monitor dimensions after rotation
            # Monitor 1: after left rotation, width = original height, height = original width
            MONITOR1_WIDTH=$MONITOR1_ORIG_HEIGHT
            MONITOR1_HEIGHT=$MONITOR1_ORIG_WIDTH
            
            # Monitor 2: same calculation
            MONITOR2_ORIG_WIDTH=$(echo "$RES2" | cut -d'x' -f1)
            MONITOR2_ORIG_HEIGHT=$(echo "$RES2" | cut -d'x' -f2)
            MONITOR2_WIDTH=$MONITOR2_ORIG_HEIGHT
            MONITOR2_HEIGHT=$MONITOR2_ORIG_WIDTH
            
            USER_DATA_DIR1="$HOME/.config/chromium-autodarts-monitor1"
            mkdir -p "$USER_DATA_DIR1"
            
            USER_DATA_DIR2="$HOME/.config/chromium-autodarts-monitor2"
            mkdir -p "$USER_DATA_DIR2"
            
            # Launch Chromium on monitor 1 (default site)
            $CHROMIUM_CMD \
                --window-position=0,0 \
                --window-size="$MONITOR1_WIDTH,$MONITOR1_HEIGHT" \
                --start-maximized \
                --disable-dev-shm-usage \
                --user-data-dir="$USER_DATA_DIR1" \
                https://play.autodarts.io &
            
            sleep 1
            
            # Launch Chromium on monitor 2 (default site - can be customized)
            $CHROMIUM_CMD \
                --window-position="$MONITOR1_WIDTH,0" \
                --window-size="$MONITOR2_WIDTH,$MONITOR2_HEIGHT" \
                --start-maximized \
                --disable-dev-shm-usage \
                --user-data-dir="$USER_DATA_DIR2" \
                https://play.autodarts.io &
        elif command -v firefox >/dev/null 2>&1; then
            firefox https://play.autodarts.io &
        else
            xdg-open https://play.autodarts.io &
        fi
    else
        # Single monitor - original behavior
        OUTPUT=$(echo "$OUTPUTS" | head -n 1)
        if [ -n "$OUTPUT" ]; then
            xrandr --output "$OUTPUT" --rotate left
            sleep 1
        fi
        
        # Launch single Chromium instance
        if command -v chromium-browser >/dev/null 2>&1; then
            USER_DATA_DIR="$HOME/.config/chromium-autodarts"
            mkdir -p "$USER_DATA_DIR"
            
            chromium-browser \
                --start-maximized \
                --disable-dev-shm-usage \
                --user-data-dir="$USER_DATA_DIR" \
                https://play.autodarts.io &
        elif command -v chromium >/dev/null 2>&1; then
            USER_DATA_DIR="$HOME/.config/chromium-autodarts"
            mkdir -p "$USER_DATA_DIR"
            
            chromium \
                --start-maximized \
                --disable-dev-shm-usage \
                --user-data-dir="$USER_DATA_DIR" \
                https://play.autodarts.io &
        elif command -v firefox >/dev/null 2>&1; then
            firefox https://play.autodarts.io &
        else
            xdg-open https://play.autodarts.io &
        fi
    fi
fi

# Keep the session running
wait
