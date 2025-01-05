#!/usr/bin/env bash
################################################################################
# driver_install.sh
#
# Script to build, install, and deploy the nc4_ili9488 driver and overlay on
# a Raspberry Pi running Debian Bookworm (or similar).
#
# Adjust paths as needed for your environment.
################################################################################

set -e

# Source the configuration file
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

LOG_FILE="$LOGS_DIR/nc4_ili9488_install.log"

# Ensure the log directory exists
mkdir -p "$LOGS_DIR"

# Clear the log file if it exists
> "$LOG_FILE"

# Enable DRM KMS debug logging
echo "==== Enabling DRM_DEBUG_KMS logging. ====" | tee -a "$LOG_FILE"
echo 0x1f | sudo tee /sys/module/drm/parameters/debug > /dev/null
if [[ $? -ne 0 ]]; then
    echo "!!ERROR!!: Failed to enable DRM_DEBUG_KMS logging. Ensure you have the necessary permissions."
    exit 1
fi

echo "==== Building and Installing the nc4_ili9488 Device Tree Overlay ====" | tee -a "$LOG_FILE"

# Navigate to the base directory
cd "$BASE_DIR"

# Compile the DTS into DTBO with verbose logging
echo "Compiling nc4_ili9488.dts -> nc4_ili9488.dtbo" | tee -a "$LOG_FILE"
dtc -@ -I dts -O dtb -o "$BUILDS_DIR/nc4_ili9488.dtbo" "$BASE_DIR/nc4_ili9488.dts" \
    |& tee -a "$LOG_FILE"

# Copy the DTBO to the overlays directory
echo "Copying nc4_ili9488.dtbo to /boot/firmware/overlays/" | tee -a "$LOG_FILE"
sudo cp "$BUILDS_DIR/nc4_ili9488.dtbo" "/boot/firmware/overlays/nc4_ili9488.dtbo" |& tee -a "$LOG_FILE"

echo "==== Building the nc4_ili9488 Kernel Module ====" | tee -a "$LOG_FILE"

# Clean old builds with verbose logging
echo "Cleaning old builds..." | tee -a "$LOG_FILE"
make clean O="$BUILDS_DIR" |& tee -a "$LOG_FILE" || true

# Compile the kernel module with verbose logging
echo "Compiling nc4_ili9488.ko..." | tee -a "$LOG_FILE"
make O="$BUILDS_DIR" |& tee -a "$LOG_FILE"

echo "==== Installing the nc4_ili9488 Kernel Module ====" | tee -a "$LOG_FILE"

# Install the kernel module
KERNEL_MODULE_DIR="/lib/modules/$(uname -r)/extra"
sudo mkdir -p "$KERNEL_MODULE_DIR" |& tee -a "$LOG_FILE"
sudo cp "$BUILDS_DIR/nc4_ili9488.ko" "$KERNEL_MODULE_DIR/" |& tee -a "$LOG_FILE"
sudo depmod -a $(uname -r) |& tee -a "$LOG_FILE"

echo "==== Done Installing nc4_ili9488 ====" | tee -a "$LOG_FILE"
echo "To enable at boot, add the following line to /boot/firmware/config.txt (if not present):" | tee -a "$LOG_FILE"
echo "  dtoverlay=nc4_ili9488" | tee -a "$LOG_FILE"

# Power off
echo "Powering off" | tee -a "$LOG_FILE"
# sudo poweroff
