#!/bin/bash

# Set the log directory and file
LOG_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs"
LOG_FILE="${LOG_DIR}/dmesg_drm.log"

# Ensure the logs directory exists
mkdir -p "$LOG_DIR"

# Run dmesg and filter for DRM-related logs, then output to both the log file and the terminal
echo "Collecting DRM-related logs..."
dmesg | grep -i drm | tee "$LOG_FILE"

# Check if the logs were successfully written
if [ $? -eq 0 ]; then
    echo "DRM logs successfully saved to $LOG_FILE"
else
    echo "Error: Failed to collect DRM logs." >&2
    exit 1
fi
