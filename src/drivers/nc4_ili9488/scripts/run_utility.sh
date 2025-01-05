#!/bin/bash
################################################################################
# run_utility.sh
#
# Purpose: Run the nc4_drm_init_util program for debugging.
################################################################################

# Load configuration
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Error handling
set -e
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Paths
UTILITY_BINARY="$UTILS_DIR/nc4_drm_init_util"
LOG_FILE="$LOGS_DIR/run_utility.log"

# Ensure log directory exists
mkdir -p "$LOGS_DIR"
> "$LOG_FILE"

# Run utility
echo "Running nc4_drm_init_util..."
sudo "$UTILITY_BINARY" >> "$LOG_FILE" 2>&1
if [[ $? -ne 0 ]]; then
    echo "!!ERROR!!: Utility execution failed. Check $LOG_FILE for details." >&2
    exit 1
fi
echo "Utility executed successfully. Logs saved to $LOG_FILE."
