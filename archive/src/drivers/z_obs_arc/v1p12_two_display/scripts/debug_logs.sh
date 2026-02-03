#!/bin/bash
################################################################################
# debug_logs.sh
#
# Purpose: Capture logs for a specified component and save them to a log file.
################################################################################

# Load configuration
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Error handling
set -e
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Arguments
COMPONENT="$1"
LOG_FILE="$LOGS_DIR/${COMPONENT}_debug.log"

# Ensure log directory exists
mkdir -p "$LOGS_DIR"
> "$LOG_FILE"

# Clean up old logs
echo "Cleaning up old journalctl logs..."
sudo journalctl --vacuum-time=1d

# Capture logs
echo "Capturing logs for $COMPONENT..."
sudo journalctl | grep "$COMPONENT" > "$LOG_FILE"

# Summarize results
if [[ -s "$LOG_FILE" ]]; then
    echo "Logs saved to $LOG_FILE."
    tail -n 10 "$LOG_FILE"
else
    echo "No logs found for $COMPONENT. Log file is empty."
fi
