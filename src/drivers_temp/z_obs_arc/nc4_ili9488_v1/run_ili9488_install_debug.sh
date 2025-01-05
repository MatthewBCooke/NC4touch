#!/bin/bash

MODULE_NAME="nc4_ili9488"
MODULE_FILE="/lib/modules/$(uname -r)/extra/${MODULE_NAME}.ko"
DRM_DEBUG_LEVEL="0x1f"
OUTPUT_FILE="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs/install_debug.log"

# Ensure the logs directory exists
mkdir -p logs

# Redirect all output to the log file
exec > >(tee -a "$OUTPUT_FILE") 2>&1

sudo modprobe drm
sudo modprobe drm_kms_helper
sudo modprobe drm_mipi_dbi
sudo modprobe drm_dma_helper

echo "==== Step 1: Compile the Kernel Module ===="
if ! make -C /lib/modules/$(uname -r)/build M=$(pwd) modules; then
    echo "Error: Module build failed." >&2
    exit 1
fi
echo "Module compiled successfully."

echo "==== Step 2: Copy the Module to /lib/modules ===="
sudo mkdir -p /lib/modules/$(uname -r)/extra/
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
if [ $? -eq 0 ]; then
    echo "Module copied to /lib/modules/$(uname -r)/extra/."
else
    echo "Error: Failed to copy module to /lib/modules/$(uname -r)/extra/." >&2
    exit 1
fi

echo "==== Step 3: Run depmod ===="
sudo depmod -a
if [ $? -eq 0 ]; then
    echo "depmod ran successfully."
else
    echo "Error: depmod failed." >&2
    exit 1
fi

echo "==== Step 4: Ensure DebugFS is Mounted ===="
if ! mount | grep -q "debugfs"; then
    echo "Mounting debugfs..."
    sudo mount -t debugfs none /sys/kernel/debug
else
    echo "DebugFS is already mounted."
fi

echo "==== Step 5: Enable DRM Debugging ===="
echo $DRM_DEBUG_LEVEL | sudo tee /sys/module/drm/parameters/debug > /dev/null
if [ $? -eq 0 ]; then
    echo "DRM debugging enabled at level $DRM_DEBUG_LEVEL."
else
    echo "Error: Failed to set DRM debug level." >&2
    exit 1
fi

echo "==== Step 6: Adjust Kernel Log Level ===="
sudo bash -c 'echo 7 > /proc/sys/kernel/printk'
if [ $? -eq 0 ]; then
    echo "Kernel log level set to verbose."
else
    echo "Error: Failed to set kernel log level." >&2
    exit 1
fi

echo "==== Step 7: Insert the Module ===="
if lsmod | grep -q "^$MODULE_NAME"; then
    sudo rmmod $MODULE_NAME || {
        echo "Error: Failed to unload module $MODULE_NAME. Exiting." >&2
        exit 1
    }
else
    echo "Module $MODULE_NAME not loaded, skipping removal."
fi

if ! sudo modprobe $MODULE_NAME; then
    echo "Error: Failed to insert module $MODULE_NAME." >&2
    exit 1
fi
echo "Module $MODULE_NAME loaded successfully."

echo "==== Step 8: Check DRM Debug Logs ===="
if dmesg | grep -i drm | tail -n 20; then
    echo "DRM debug messages displayed above."
else
    echo "No DRM debug messages found. Ensure DRM debugging is enabled and functional."
fi

echo "==== Step 9: Verify Module Status ===="
lsmod | grep $MODULE_NAME && echo "Module $MODULE_NAME is loaded." || echo "Module $MODULE_NAME is not loaded."

echo "==== Step 10: Verify DebugFS and DRM Entries ===="
if [ -d "/sys/kernel/debug/dri" ]; then
    echo "DebugFS entries for DRM found:"
    ls /sys/kernel/debug/dri/0/ || echo "No DRM debug entries found."
else
    echo "No DebugFS entries for DRM. Ensure DRM is configured correctly in the kernel."
fi

echo "==== Step 11: Review Module Info ===="
modinfo $MODULE_FILE || echo "Module info not available for $MODULE_FILE."

echo "==== Script Complete ===="
