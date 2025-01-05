#!/bin/bash
# ==========================================================
# Journalctl Log Capture for nc4_drm_init_util
# ----------------------------------------------------------
# This script captures journalctl logs related to the
# nc4_drm_init_util utility and saves them in a log file
# within the configured logs directory.
# ----------------------------------------------------------
# Prerequisites:
# - Ensure the config.env file is set up correctly.
# - Run this script with sufficient permissions if required
#   to access journalctl (e.g., via sudo).
# ==========================================================

set -e

# Load configuration from config.env
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Configuration variables
LOG_FILE="$LOGS_DIR/nc4_drm_init_util_debug.log"

# Ensure the log directory exists
mkdir -p "$LOGS_DIR"

# Clear the log file if it exists
> "$LOG_FILE"

# Clean up journalctl logs older than one day
echo "Cleaning up journalctl logs older than one day..."
sudo journalctl --vacuum-time=1d

# Capture journalctl logs for the nc4_drm_init_util utility
echo "Capturing journalctl logs for nc4_drm_init_util..."
sudo journalctl | grep "nc4_drm_init_util" > "$LOG_FILE"

# Print a summary to the console
if [[ -s "$LOG_FILE" ]]; then
    log_count=$(wc -l < "$LOG_FILE")
    echo "Logs for nc4_drm_init_util saved to $LOG_FILE."
    echo "Number of matching log entries: $log_count"
    echo "Last 10 entries:"
    tail -n 10 "$LOG_FILE"
else
    echo "No logs found for nc4_drm_init_util. Log file created but is empty."
fi

# Done
echo "Log capture complete. Logs are stored in $LOG_FILE."
