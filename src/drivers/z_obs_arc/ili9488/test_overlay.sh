#!/bin/bash
DTS_FILE="/home/nc4/TouchscreenApparatus/src/drivers/z_obs_arc/ili9488/rpi-overlays/ili9488.dts"
DTBO_FILE="/boot/firmware/overlays/ili9488.dtbo"

echo "==== Unloading Driver ===="
if lsmod | grep -q "ili9488"; then
    echo "Driver 'ili9488' is loaded. Removing it..."
    if ! sudo modprobe -r ili9488; then
        echo "Error: Failed to remove driver 'ili9488'."
        exit 1
    fi
else
    echo "Driver 'ili9488' is not currently loaded."
fi

echo "==== Cleaning up overlays ===="
sudo rmdir /sys/kernel/config/device-tree/overlays/* 2>/dev/null || echo "No overlays to remove."

echo "==== Compiling the .dts file ===="
if ! sudo dtc -@ -I dts -O dtb -o "$DTBO_FILE" "$DTS_FILE"; then
    echo "Error: Failed to compile $DTS_FILE."
    exit 1
fi

echo "==== Applying the overlay ===="
if ! sudo dtoverlay -v ili9488; then
    echo "Error: Failed to apply overlay."
    dmesg | tail -50
    exit 1
fi

echo "==== Running Validation ===="
/home/nc4/TouchscreenApparatus/src/drivers/z_obs_arc/ili9488/verify_ili9488.sh
