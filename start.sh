#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly DEFAULT_SITE="https://play.autodarts.io/boards/62f17919-bbb2-443b-bf0e-a5d6e27c7898/follow"
readonly LOG_DIR="${HOME}/.local/log"
readonly MOUSE_DEV="${MOUSE_DEV:-YOUR_MOUSE_NAME}"  # Override with environment variable

# X display setup
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $SCRIPT_NAME: $*" | tee -a "${LOG_DIR}/start.sh.log" >&2
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit "${2:-1}"
}

# Find Chromium executable
find_chromium() {
    local chromium_paths=(
        "/usr/lib/chromium/chromium"
        "/usr/bin/chromium-browser"
        "/usr/bin/chromium"
    )
    
    for path in "${chromium_paths[@]}"; do
        if [ -f "$path" ] || command -v "$path" >/dev/null 2>&1; then
            echo "$path"
            return 0
        fi
    done
    
    # Try to find in PATH
    if command -v chromium-browser >/dev/null 2>&1; then
        command -v chromium-browser
        return 0
    elif command -v chromium >/dev/null 2>&1; then
        command -v chromium
        return 0
    fi
    
    return 1
}

# Fix Chromium crash state
fix_chromium_crash_state() {
    local prefs_file="$1"
    if [ -f "$prefs_file" ]; then
        sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$prefs_file" 2>/dev/null || true
        sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "$prefs_file" 2>/dev/null || true
    fi
}

# Get monitor information from xrandr
get_monitor_info() {
    local output="$1"
    local info_type="$2"  # "resolution", "position", "rotation"
    
    case "$info_type" in
        resolution)
            xrandr --query 2>/dev/null | \
                grep -A 10 "^${output}" | \
                grep -E "^\s+[0-9]+x[0-9]+" | \
                head -n 1 | \
                awk '{print $1}' || true
            ;;
        position)
            xrandr --query 2>/dev/null | \
                grep "^${output}" | \
                grep -oE '\+[0-9]+\+[0-9]+' | \
                head -n 1 || true
            ;;
        rotation)
            xrandr --query 2>/dev/null | \
                grep "^${output}" | \
                grep -oE '\s+(left|right|normal|inverted)\s+' | \
                head -n 1 | \
                tr -d ' ' || echo "normal"
            ;;
    esac
}

# Calculate monitor dimensions accounting for rotation
calculate_dimensions() {
    local resolution="$1"
    local rotation="${2:-normal}"
    local orig_width orig_height
    
    orig_width=$(echo "$resolution" | cut -d'x' -f1)
    orig_height=$(echo "$resolution" | cut -d'x' -f2)
    
    if [ "$rotation" = "left" ] || [ "$rotation" = "right" ]; then
        echo "${orig_height}x${orig_width}"
    else
        echo "${orig_width}x${orig_height}"
    fi
}

# Launch Chromium on a specific monitor
launch_chromium_monitor() {
    local monitor_num="$1"
    local url="$2"
    local x_pos="$3"
    local y_pos="$4"
    local width="$5"
    local height="$6"
    local chromium_cmd="$7"
    
    local user_data_dir="${HOME}/.config/chromium-autodarts-monitor${monitor_num}"
    local log_file="${LOG_DIR}/chromium-monitor${monitor_num}.log"
    
    mkdir -p "$user_data_dir"
    fix_chromium_crash_state "${user_data_dir}/Default/Preferences"
    
    # Get existing windows before launch
    local existing_windows=""
    if command -v xdotool >/dev/null 2>&1; then
        existing_windows=$(xdotool search --class chromium 2>/dev/null || true)
    fi
    
    log "Launching Chromium for monitor ${monitor_num} with URL: ${url:-default}"
    
    # Launch Chromium
    "$chromium_cmd" \
        --kiosk \
        --disable-session-crashed-bubble \
        --disable-breakpad \
        --disable-infobars \
        --disable-suggestions-ui \
        --disable-translate \
        --user-data-dir="$user_data_dir" \
        "${url:-$DEFAULT_SITE}" \
        >"$log_file" 2>&1 &
    
    local chromium_pid=$!
    log "Chromium PID for monitor ${monitor_num}: $chromium_pid"
    
    # Wait and position window if xdotool is available
    if command -v xdotool >/dev/null 2>&1; then
        sleep 3
        local all_windows new_window
        all_windows=$(xdotool search --class chromium 2>/dev/null || true)
        
        for window_id in $all_windows; do
            if ! echo "$existing_windows" | grep -q "^${window_id}$"; then
                new_window="$window_id"
                break
            fi
        done
        
        if [ -n "${new_window:-}" ]; then
            xdotool windowmove "$new_window" "$x_pos" "$y_pos" 2>/dev/null || true
            xdotool windowsize "$new_window" "$width" "$height" 2>/dev/null || true
            log "Positioned window $new_window at (${x_pos}, ${y_pos}) size ${width}x${height}"
        fi
    else
        log "WARNING: xdotool not found - window positioning skipped"
    fi
}

# Parse arguments and determine monitor configuration
parse_arguments() {
    local arg1="${1:-}"
    local arg2="${2:-}"
    
    # Determine which monitors to use and their URLs
    if [ -n "$arg1" ] && [ -n "$arg2" ]; then
        # Both monitors: [url1, url2]
        SITE1="$arg1"
        SITE2="$arg2"
        USE_MONITOR1=true
        USE_MONITOR2=true
    elif [ -z "$arg1" ] && [ -n "$arg2" ]; then
        # Monitor 2 only: ['', url2]
        SITE1="$DEFAULT_SITE"
        SITE2="$arg2"
        USE_MONITOR1=false
        USE_MONITOR2=true
    elif [ -n "$arg1" ] && [ -z "$arg2" ]; then
        # Monitor 1 only: [url1]
        SITE1="$arg1"
        SITE2="$DEFAULT_SITE"
        USE_MONITOR1=true
        USE_MONITOR2=false
    else
        # No arguments: use defaults for both
        SITE1="$DEFAULT_SITE"
        SITE2="$DEFAULT_SITE"
        USE_MONITOR1=true
        USE_MONITOR2=true
    fi
}

# Main execution
main() {
    log "Starting display script"
    
    # Parse arguments
    parse_arguments "${1:-}" "${2:-}"
    
    # Disable mouse if configured
    if [ "$MOUSE_DEV" != "YOUR_MOUSE_NAME" ]; then
        xinput disable "$MOUSE_DEV" 2>/dev/null || log "Mouse '$MOUSE_DEV' not found or already disabled"
    fi
    
    # Kill existing Chromium instances
    log "Killing existing Chromium instances"
    pkill -9 -f chromium 2>/dev/null || true
    sleep 1
    
    # Fix crash states for all potential user data directories
    local prefs_dirs=(
        "${HOME}/.config/chromium-autodarts-monitor1/Default/Preferences"
        "${HOME}/.config/chromium-autodarts-monitor2/Default/Preferences"
        "${HOME}/.config/chromium-autodarts/Default/Preferences"
        "${HOME}/.config/chromium/Default/Preferences"
    )
    
    for prefs_file in "${prefs_dirs[@]}"; do
        fix_chromium_crash_state "$prefs_file"
    done
    
    # Find Chromium executable
    CHROMIUM_CMD=$(find_chromium) || error_exit "Chromium not found. Please install Chromium."
    log "Using Chromium: $CHROMIUM_CMD"
    
    # Detect connected monitors
    local outputs
    outputs=$(xrandr --query 2>/dev/null | grep " connected" | cut -d' ' -f1 || true)
    local output_count
    output_count=$(echo "$outputs" | grep -c . || echo "0")
    
    if [ "$output_count" -eq 2 ]; then
        # Dual monitor setup
        log "Detected 2 monitors"
        
        OUTPUT1=$(echo "$outputs" | head -n 1)
        OUTPUT2=$(echo "$outputs" | tail -n 1)
        
        xrandr --output "$OUTPUT1" --primary >/dev/null 2>&1 || true
        
        # Get monitor information
        local res1 res2 pos1 pos2 rot1 rot2
        res1=$(get_monitor_info "$OUTPUT1" "resolution")
        res2=$(get_monitor_info "$OUTPUT2" "resolution")
        pos1=$(get_monitor_info "$OUTPUT1" "position")
        pos2=$(get_monitor_info "$OUTPUT2" "position")
        rot1=$(get_monitor_info "$OUTPUT1" "rotation")
        rot2=$(get_monitor_info "$OUTPUT2" "rotation")
        
        # Extract positions
        local x1 y1 x2 y2
        x1=$(echo "$pos1" | sed 's/^+\([0-9]*\)+.*/\1/' 2>/dev/null || echo "0")
        y1=$(echo "$pos1" | sed 's/^+[0-9]*+\([0-9]*\)/\1/' 2>/dev/null || echo "0")
        x2=$(echo "$pos2" | sed 's/^+\([0-9]*\)+.*/\1/' 2>/dev/null || echo "0")
        y2=$(echo "$pos2" | sed 's/^+[0-9]*+\([0-9]*\)/\1/' 2>/dev/null || echo "0")
        
        # Calculate dimensions with rotation
        local dims1 dims2 width1 height1 width2 height2
        dims1=$(calculate_dimensions "$res1" "$rot1")
        dims2=$(calculate_dimensions "$res2" "$rot2")
        width1=$(echo "$dims1" | cut -d'x' -f1)
        height1=$(echo "$dims1" | cut -d'x' -f2)
        width2=$(echo "$dims2" | cut -d'x' -f1)
        height2=$(echo "$dims2" | cut -d'x' -f2)
        
        # Calculate X2 if not detected
        if [ "$x2" = "0" ] && [ "$y2" = "0" ] && [ -n "$res1" ]; then
            local monitor1_orig_width
            monitor1_orig_width=$(echo "$res1" | cut -d'x' -f1)
            local monitor1_orig_height
            monitor1_orig_height=$(echo "$res1" | cut -d'x' -f2)
            
            if [ "$rot1" = "left" ] || [ "$rot1" = "right" ]; then
                x2=$monitor1_orig_height
            else
                x2=$monitor1_orig_width
            fi
            y2=0
        fi
        
        # Launch monitor 1 if requested
        if [ "$USE_MONITOR1" = "true" ]; then
            launch_chromium_monitor 1 "$SITE1" "$x1" "$y1" "$width1" "$height1" "$CHROMIUM_CMD"
        fi
        
        # Launch monitor 2 if requested
        if [ "$USE_MONITOR2" = "true" ]; then
            sleep 2  # Stagger launches slightly
            launch_chromium_monitor 2 "$SITE2" "$x2" "$y2" "$width2" "$height2" "$CHROMIUM_CMD"
        fi
        
    else
        # Single monitor setup
        log "Detected 1 monitor"
        
        local single_site user_data_dir
        if [ "$USE_MONITOR2" = "true" ] && [ "$USE_MONITOR1" = "false" ]; then
            single_site="$SITE2"
            user_data_dir="${HOME}/.config/chromium-autodarts-monitor2"
        else
            single_site="$SITE1"
            user_data_dir="${HOME}/.config/chromium-autodarts"
        fi
        
        mkdir -p "$user_data_dir"
        fix_chromium_crash_state "${user_data_dir}/Default/Preferences"
        
        log "Launching Chromium for single monitor with URL: ${single_site:-default}"
        
        "$CHROMIUM_CMD" \
            --kiosk \
            --disable-session-crashed-bubble \
            --disable-breakpad \
            --disable-infobars \
            --disable-suggestions-ui \
            --disable-translate \
            --user-data-dir="$user_data_dir" \
            "${single_site:-$DEFAULT_SITE}" \
            >"${LOG_DIR}/chromium-single.log" 2>&1 &
        
        log "Single monitor Chromium launched (PID: $!)"
    fi
    
    log "Display script completed successfully"
}

# Run main function
main "$@"
