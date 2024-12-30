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

echo "==== Building and Installing the nc4_ili9488 Device Tree Overlay ===="
# Compile the DTS into DTBO
DTS_FILE="nc4_ili9488.dts"
DTB_FILE="nc4_ili9488.dtbo"
OVERLAY_TARGET="/boot/firmware/overlays/${DTB_FILE}"

cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488

echo "Compiling $DTS_FILE -> $DTB_FILE"
dtc -@ -I dts -O dtb -o "$DTB_FILE" "$DTS_FILE"

echo "Copying $DTB_FILE to $OVERLAY_TARGET"
sudo cp "$DTB_FILE" "$OVERLAY_TARGET"

echo "==== Building the nc4_ili9488 Kernel Module ===="
# Build the kernel module
echo "Cleaning old builds..."
make clean || true

echo "Compiling nc4_ili9488.ko..."
make

echo "==== Installing the nc4_ili9488 Kernel Module ===="
sudo mkdir -p /lib/modules/$(uname -r)/extra
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a $(uname -r)

echo "==== Done Installing nc4_ili9488 ===="
echo "To enable at boot, add the following line to /boot/firmware/config.txt (if not present):"
echo "  dtoverlay=nc4_ili9488"

echo "Powering off"
sudo poweroff
