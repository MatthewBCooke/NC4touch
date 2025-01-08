#!/bin/bash
################################################################################
# compile_utility.sh
#
# Purpose: Compile the nc4_drm_init_util program for debugging.
################################################################################

# Load configuration
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Error handling
set -e
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Paths
UTILITY_SOURCE="$UTILS_DIR/nc4_drm_init_util.c"
UTILITY_BINARY="$UTILS_DIR/nc4_drm_init_util"
LOG_FILE="$LOGS_DIR/compile_utility.log"

# Ensure log directory exists
mkdir -p "$LOGS_DIR"
> "$LOG_FILE"

# Compile utility
echo "Compiling nc4_drm_init_util..."
gcc -I/usr/include/drm "$UTILITY_SOURCE" -o "$UTILITY_BINARY" -ldrm 2>> "$LOG_FILE"
if [[ -f "$UTILITY_BINARY" ]]; then
    echo "Utility compiled successfully: $UTILITY_BINARY"
else
    echo "!!ERROR!!: Compilation failed. Check $LOG_FILE for details." >&2
    exit 1
fi
