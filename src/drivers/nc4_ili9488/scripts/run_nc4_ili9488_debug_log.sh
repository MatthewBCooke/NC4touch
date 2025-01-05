#!/bin/bash
# ==========================================================
# DRM KMS Debugging Script for nc4_ili9488
# ----------------------------------------------------------
# This script enables DRM KMS debug logging, captures logs
# specific to the nc4_ili9488 driver, and saves them to a
# log file in the configured logs directory.
# ----------------------------------------------------------
# Prerequisites:
# - Ensure the config.env file is set up correctly.
# - Run this script with sufficient permissions to modify
#   kernel parameters (e.g., via sudo).
# ==========================================================

set -e

# Load configuration from config.env
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Configuration variables
DRIVER_NAME="nc4_ili9488"
LOG_FILE="$LOGS_DIR/nc4_ili9488_debug.log"

# Ensure the log directory exists
mkdir -p "$LOGS_DIR"

# Clear the log file if it exists
> "$LOG_FILE"

# Clean up journalctl logs older than one day
echo "Cleaning up journalctl logs older than one day..."
sudo journalctl --vacuum-time=1d

# Capture logs related to the driver
echo "Capturing logs for $DRIVER_NAME..."
dmesg | grep "$DRIVER_NAME" > "$LOG_FILE"

# Print a summary to the console
if [[ -s "$LOG_FILE" ]]; then
    log_count=$(wc -l < "$LOG_FILE")
    echo "Logs for nc4_ili9488 saved to $LOG_FILE."
    echo "Number of matching log entries: $log_count"
    echo "Last 10 entries:"
    tail -n 10 "$LOG_FILE"
else
    echo "No logs found for nc4_ili9488. Log file created but is empty."
fi

# Done
echo "Logging complete. Logs are saved in $LOG_FILE."

