#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_DIR="${HOME}/.local/log"
readonly AUTO_START="${AUTO_START:-false}"  # Set to true to auto-start Chromium after waking

# X display setup
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SCRIPT_NAME: $*" | tee -a "${LOG_DIR}/wake-screen.log" >&2
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit "${2:-1}"
}

# Get monitor information from xrandr
get_monitor_resolution() {
    local output="$1"
    xrandr --query 2>/dev/null | \
        grep -A 10 "^${output}" | \
        grep -E "^\s+[0-9]+x[0-9]+" | \
        head -n 1 | \
        awk '{print $1}' || true
}

# Turn on displays
turn_on_displays() {
    local outputs
    outputs=$(xrandr --query 2>/dev/null | grep " connected" | cut -d' ' -f1 || true)
    
    if [ -z "$outputs" ]; then
        log "No connected displays found via xrandr"
        return 1
    fi
    
    local output_count
    output_count=$(echo "$outputs" | grep -c . || echo "0")
    
    log "Found $output_count connected display(s)"
    
    if [ "$output_count" -eq 2 ]; then
        # Dual monitor setup
        local output1 output2 res1 res2
        output1=$(echo "$outputs" | head -n 1)
        output2=$(echo "$outputs" | tail -n 1)
        
        res1=$(get_monitor_resolution "$output1")
        res2=$(get_monitor_resolution "$output2")
        
        if [ -z "$res1" ]; then
            res1=$(xrandr --query 2>/dev/null | grep -A 10 "^${output1}" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}' || echo "")
        fi
        if [ -z "$res2" ]; then
            res2=$(xrandr --query 2>/dev/null | grep -A 10 "^${output2}" | grep -E "[0-9]+x[0-9]+" | head -n 1 | awk '{print $1}' || echo "")
        fi
        
        log "Configuring dual monitor setup"
        log "Monitor 1: $output1 (${res1:-auto})"
        log "Monitor 2: $output2 (${res2:-auto})"
        
        # Configure first monitor
        if [ -n "$res1" ]; then
            xrandr --output "$output1" --auto --primary --mode "$res1" --rotate left 2>/dev/null || \
            xrandr --output "$output1" --auto --primary --rotate left 2>/dev/null || \
            xrandr --output "$output1" --auto --primary 2>/dev/null || \
            log "Warning: Failed to configure $output1 optimally"
        else
            xrandr --output "$output1" --auto --primary 2>/dev/null || \
            log "Warning: Failed to configure $output1"
        fi
        
        # Calculate position for second monitor (after rotation, width = original height)
        local monitor1_width monitor1_height x2_pos
        if [ -n "$res1" ]; then
            monitor1_width=$(echo "$res1" | cut -d'x' -f1)
            monitor1_height=$(echo "$res1" | cut -d'x' -f2)
            x2_pos=$monitor1_height  # After left rotation
        else
            x2_pos=1080  # Default fallback
        fi
        
        # Configure second monitor
        if [ -n "$res2" ]; then
            xrandr --output "$output2" --auto --mode "$res2" --pos "${x2_pos}x0" --rotate left 2>/dev/null || \
            xrandr --output "$output2" --auto --pos "${x2_pos}x0" --rotate left 2>/dev/null || \
            xrandr --output "$output2" --auto --rotate left 2>/dev/null || \
            log "Warning: Failed to configure $output2 optimally"
        else
            xrandr --output "$output2" --auto --rotate left 2>/dev/null || \
            log "Warning: Failed to configure $output2"
        fi
        
        sleep 1
        
    elif [ "$output_count" -eq 1 ]; then
        # Single monitor setup
        local output res
        output=$(echo "$outputs" | head -n 1)
        res=$(get_monitor_resolution "$output")
        
        log "Configuring single monitor: $output (${res:-auto})"
        
        if [ -n "$res" ]; then
            xrandr --output "$output" --auto --mode "$res" --rotate left 2>/dev/null || \
            xrandr --output "$output" --auto --rotate left 2>/dev/null || \
            xrandr --output "$output" --auto 2>/dev/null || \
            log "Warning: Failed to configure $output optimally"
        else
            xrandr --output "$output" --auto 2>/dev/null || \
            log "Warning: Failed to configure $output"
        fi
        
        sleep 1
    fi
    
    return 0
}

# Main execution
main() {
    log "Starting wake screen operation"
    
    # Turn displays back on using vcgencmd (Raspberry Pi specific)
    log "Attempting to wake displays using vcgencmd"
    if command -v vcgencmd >/dev/null 2>&1; then
        sudo vcgencmd display_power 1 2>/dev/null || \
        vcgencmd display_power 1 2>/dev/null || \
        log "vcgencmd display_power failed (may require sudo or not available)"
    else
        log "vcgencmd not found, skipping hardware display power control"
    fi
    
    # Turn on displays using xrandr
    if ! turn_on_displays; then
        error_exit "Failed to turn on displays"
    fi
    
    # Wait for displays to stabilize
    sleep 1
    
    log "Displays woken successfully"
    
    # Optionally start Chromium if AUTO_START is enabled
    if [ "$AUTO_START" = "true" ] && [ -f "${HOME}/start.sh" ]; then
        log "AUTO_START enabled, launching start.sh"
        "${HOME}/start.sh" >"${LOG_DIR}/start-from-wake.log" 2>&1 &
        log "start.sh launched in background (PID: $!)"
    fi
}

# Run main function
main "$@"
