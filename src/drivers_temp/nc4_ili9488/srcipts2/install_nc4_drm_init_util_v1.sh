#!/usr/bin/env bash
################################################################################
# run_nc4_drm_init_util_install.sh
#
# Script to build, execute, and validate the nc4_drm_init_util program for
# initializing DRM-based displays.
#
# Adjust paths as needed for your environment.
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
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Ensure the log directory exists
mkdir -p "$LOG_DIR"

# Delete the old log file if it exists
if [[ -f "$LOG_FILE" ]]; then
    echo "Removing old log file: $LOG_FILE"
    rm "$LOG_FILE"
fi

# Ensure the log directory is writable
if [[ ! -w "$LOG_DIR" ]]; then
    echo "!!ERROR!!: Cannot write to log directory: $LOG_DIR"
    exit 1
fi

echo "==== Compiling nc4_drm_init_util ===="

# Compile the DRM initialization utility
gcc -I/usr/include/drm "$UTILITY_SOURCE" -o "$UTILITY_BINARY" -ldrm
if [[ -f "$UTILITY_BINARY" ]]; then
    echo "Compiled successfully: $UTILITY_BINARY"
else
    echo "!!ERROR!!: Compilation failed."
    exit 1
fi

echo
echo "==== Executing nc4_drm_init_util ===="

# Run the utility with elevated privileges
sudo "$UTILITY_BINARY"
if [[ $? -ne 0 ]]; then
    echo "!!ERROR!!: nc4_drm_init_util execution failed."
    exit 1
fi

echo
echo "==== Validating DRM Initialization ===="

# Check for relevant debug messages in journalctl
echo "Searching kernel logs for nc4_drm_init_util debug messages..."
sudo journalctl | grep "nc4_drm_init_util" > "$LOG_FILE"
if [[ -s "$LOG_FILE" ]]; then
    echo "Logs saved to $LOG_FILE"
    echo "Number of matching log entries: $(wc -l < "$LOG_FILE")"
else
    echo "No debug messages found for nc4_drm_init_util."
fi

echo
echo "==== Done ===="
