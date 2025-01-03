#!/bin/bash

# Configuration
DRIVER_NAME="nc4_ili9488"
LOG_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs"
LOG_FILE="$LOG_DIR/kms_debug.log"

# Ensure the log directory exists
mkdir -p "$LOG_DIR"

# Delete the old log file if it exists
if [[ -f "$LOG_FILE" ]]; then
    rm "$LOG_FILE"
fi

# Enable DRM KMS debug logging
echo "Enabling DRM_DEBUG_KMS logging..."
echo 0x1f | sudo tee /sys/module/drm/parameters/debug > /dev/null
if [[ $? -ne 0 ]]; then
    echo "!!ERROR!!: Failed to enable DRM_DEBUG_KMS logging. Ensure you have the necessary permissions."
    exit 1
fi

# Capture logs related to the driver
echo "Capturing logs for $DRIVER_NAME..."
dmesg | grep "nc4_ili9488" > "$LOG_FILE"

# Print the logs to the console
echo "Relevant logs for $DRIVER_NAME (saved to $LOG_FILE):"
cat "$LOG_FILE"

# Done
echo "Logging complete. Logs are saved in $LOG_FILE."
