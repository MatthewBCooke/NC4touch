#!/usr/bin/env bash
################################################################################
# run_drm_init_utility_install.sh
#
# Script to build, execute, and validate the drm_init_utility program for
# initializing DRM-based displays.
#
# Adjust paths as needed for your environment.
################################################################################

set -e

# Paths
UTILITY_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/drm_init_utility"
LOG_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs"
LOG_FILE="$LOG_DIR/drm_debug.log"
UTILITY_SOURCE="$UTILITY_DIR/drm_init_utility.c"
UTILITY_BINARY="$UTILITY_DIR/drm_init_utility"

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

echo "==== Compiling drm_init_utility ===="

# Compile the DRM initialization utility
gcc -I/usr/include/drm "$UTILITY_SOURCE" -o "$UTILITY_BINARY" -ldrm
if [[ -f "$UTILITY_BINARY" ]]; then
    echo "Compiled successfully: $UTILITY_BINARY"
else
    echo "!!ERROR!!: Compilation failed."
    exit 1
fi

echo
echo "==== Executing drm_init_utility ===="

# Run the utility with elevated privileges
sudo "$UTILITY_BINARY"
if [[ $? -ne 0 ]]; then
    echo "!!ERROR!!: drm_init_utility execution failed."
    exit 1
fi

echo
echo "==== Validating DRM Initialization ===="

# Check for relevant debug messages in journalctl
echo "Searching kernel logs for drm_init_utility debug messages..."
sudo journalctl | grep "drm_init_utility" > "$LOG_FILE"
if [[ -s "$LOG_FILE" ]]; then
    echo "Logs saved to $LOG_FILE"
    echo "Number of matching log entries: $(wc -l < "$LOG_FILE")"
else
    echo "No debug messages found for drm_init_utility."
fi

echo
echo "==== Done ===="
