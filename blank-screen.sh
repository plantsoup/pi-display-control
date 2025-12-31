#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_DIR="${HOME}/.local/log"

# X display setup
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SCRIPT_NAME: $*" | tee -a "${LOG_DIR}/blank-screen.log" >&2
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit "${2:-1}"
}

# Main execution
main() {
    log "Starting blank screen operation"
    
    # Kill Chromium first (it might be keeping displays on)
    log "Killing Chromium processes"
    pkill -9 -f chromium 2>/dev/null || log "No Chromium processes found"
    
    # Wait for Chromium to fully close
    sleep 1
    
    # Try to blank screens using vcgencmd (Raspberry Pi specific)
    log "Attempting to blank displays using vcgencmd"
    if command -v vcgencmd >/dev/null 2>&1; then
        sudo vcgencmd display_power 0 2>/dev/null || log "vcgencmd display_power failed (may require sudo)"
    else
        log "vcgencmd not found, skipping hardware display power control"
    fi
    
    # Get all connected displays
    local outputs
    outputs=$(xrandr --query 2>/dev/null | grep " connected" | cut -d' ' -f1 || true)
    
    if [ -z "$outputs" ]; then
        log "No connected displays found via xrandr"
        return 0
    fi
    
    # Turn off all connected displays using xrandr
    log "Turning off displays using xrandr"
    local output_count=0
    while IFS= read -r output; do
        if [ -n "$output" ]; then
            log "Turning off display: $output"
            xrandr --output "$output" --off 2>/dev/null || log "Failed to turn off $output"
            ((output_count++)) || true
        fi
    done <<< "$outputs"
    
    log "Blanked $output_count display(s) successfully"
}

# Run main function
main "$@"
