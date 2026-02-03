#!/bin/bash

MODULE_NAME="debug_test"
MODULE_FILE="${MODULE_NAME}.ko"
DRM_DEBUG_LEVEL="0x1f"

echo "==== Step 1: Compile the Kernel Module ===="
if ! make; then
    echo "Error: Module build failed." >&2
    exit 1
fi
echo "Module compiled successfully."

echo "==== Step 2: Ensure DebugFS is Mounted ===="
if ! mount | grep -q "debugfs"; then
    echo "Mounting debugfs..."
    sudo mount -t debugfs none /sys/kernel/debug
else
    echo "DebugFS is already mounted."
fi

echo "==== Step 3: Enable DRM Debugging ===="
echo $DRM_DEBUG_LEVEL | sudo tee /sys/module/drm/parameters/debug > /dev/null
if [ $? -eq 0 ]; then
    echo "DRM debugging enabled at level $DRM_DEBUG_LEVEL."
else
    echo "Error: Failed to set DRM debug level." >&2
    exit 1
fi

echo "==== Step 4: Adjust Kernel Log Level ===="
sudo bash -c 'echo 7 > /proc/sys/kernel/printk'
if [ $? -eq 0 ]; then
    echo "Kernel log level set to verbose."
else
    echo "Error: Failed to set kernel log level." >&2
    exit 1
fi

echo "==== Step 5: Insert the Module ===="
sudo rmmod $MODULE_NAME 2>/dev/null || echo "Module $MODULE_NAME not loaded, skipping removal."
if ! sudo insmod $MODULE_FILE; then
    echo "Error: Failed to insert module $MODULE_NAME." >&2
    exit 1
fi
echo "Module $MODULE_NAME loaded successfully."

echo "==== Step 6: Check DRM Debug Logs ===="
if dmesg | grep -i drm | tail -n 20; then
    echo "DRM debug messages displayed above."
else
    echo "No DRM debug messages found. Ensure DRM debugging is enabled and functional."
fi

echo "==== Step 7: Verify Module Status ===="
lsmod | grep $MODULE_NAME && echo "Module $MODULE_NAME is loaded." || echo "Module $MODULE_NAME is not loaded."

echo "==== Step 8: Verify DebugFS and DRM Entries ===="
if [ -d "/sys/kernel/debug/dri" ]; then
    echo "DebugFS entries for DRM found:"
    ls /sys/kernel/debug/dri/0/ || echo "No DRM debug entries found."
else
    echo "No DebugFS entries for DRM. Ensure DRM is configured correctly in the kernel."
fi

echo "==== Step 9: Review Module Info ===="
modinfo $MODULE_FILE || echo "Module info not available for $MODULE_FILE."

echo "==== Script Complete ===="
