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
PROJECT_ROOT="/home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug"
UTILITY_SOURCE="$PROJECT_ROOT/drm_init_utility/drm_init_utility.c"
UTILITY_BINARY="$PROJECT_ROOT/drm_init_utility/drm_init_utility"
DEBUG_LOG="$PROJECT_ROOT/logs/drm_debug.log"

# Error trap
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Ensure log directory is writable
if [[ ! -w "$PROJECT_ROOT/logs" ]]; then
    echo "!!ERROR!!: Cannot write to log directory: $PROJECT_ROOT/logs"
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

# Check for relevant debug messages in dmesg
echo "Searching kernel logs for drm_init_utility debug messages..."
sudo journalctl | grep "nc4_ili9488: [drm_init_utility]" > "$DEBUG_LOG"
if [[ -s "$DEBUG_LOG" ]]; then
    echo "Logs saved to $DEBUG_LOG"
    echo "Captured debug messages:"
    cat "$DEBUG_LOG"
else
    echo "No debug messages found for drm_init_utility."
fi

echo
echo "==== Done ===="
