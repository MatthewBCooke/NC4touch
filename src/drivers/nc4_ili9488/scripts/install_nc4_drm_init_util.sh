#!/usr/bin/env bash
################################################################################
#
# Script to build, execute, and validate the nc4_drm_init_util program for
# initializing DRM-based displays.
#
################################################################################

set -e

# Source the configuration file
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Define utility and log paths using sourced variables
UTILITY_DIR="$UTILS_DIR"
LOG_DIR="$LOGS_DIR"
LOG_FILE="$LOG_DIR/install_nc4_drm_init_util.log"
UTILITY_SOURCE="$UTILITY_DIR/nc4_drm_init_util.c"
UTILITY_BINARY="$UTILITY_DIR/nc4_drm_init_util"

# Error trap
trap 'echo "!!ERROR!!: Script failed at line $LINENO." | tee -a "$LOG_FILE"; exit 1;' ERR

# Ensure the log directory exists
mkdir -p "$LOGS_DIR"

# Clear the log file if it exists
> "$LOG_FILE"

echo "==== Compiling nc4_drm_init_util ====" | tee -a "$LOG_FILE"

# Compilation with error logging
gcc -I/usr/include/drm "$UTILITY_SOURCE" -o "$UTILITY_BINARY" -ldrm 2>> "$LOG_FILE"
if [[ -f "$UTILITY_BINARY" ]]; then
    echo "Compiled successfully: $UTILITY_BINARY" | tee -a "$LOG_FILE"
else
    echo "!!ERROR!!: Compilation failed. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo | tee -a "$LOG_FILE"
echo "==== Executing nc4_drm_init_util ====" | tee -a "$LOG_FILE"

# Execution with full logging
sudo "$UTILITY_BINARY" >> "$LOG_FILE" 2>&1
if [[ $? -ne 0 ]]; then
    echo "!!ERROR!!: nc4_drm_init_util execution failed. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    exit 1
fi

echo | tee -a "$LOG_FILE"
echo "==== Validating DRM Initialization ====" | tee -a "$LOG_FILE"

# Record the start time for journal filtering
START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# Check for relevant debug messages in journalctl
echo "Searching kernel logs for nc4_drm_init_util debug messages..." | tee -a "$LOG_FILE"
sudo journalctl --since "$START_TIME" | grep "nc4_drm_init_util" >> "$LOG_FILE" 2>&1
if [[ -s "$LOG_FILE" ]]; then
    echo "Logs saved to $LOG_FILE" | tee -a "$LOG_FILE"
    echo "Number of matching log entries: $(wc -l < "$LOG_FILE")" | tee -a "$LOG_FILE"
else
    echo "No debug messages found for nc4_drm_init_util." | tee -a "$LOG_FILE"
fi

echo | tee -a "$LOG_FILE"
echo "==== Done ====" | tee -a "$LOG_FILE"
