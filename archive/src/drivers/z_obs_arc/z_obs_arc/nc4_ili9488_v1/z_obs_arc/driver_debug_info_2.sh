#!/bin/bash

MODULE_NAME="nc4_ili9488"
MODULE_FILE="/lib/modules/$(uname -r)/extra/${MODULE_NAME}.ko"
KERNEL_HEADERS="/lib/modules/$(uname -r)/build"
DRM_MODULES=("drm" "drm_kms_helper" "drm_mipi_dbi" "drm_dma_helper")

echo "==== Step 1: Verify Kernel Headers ===="
if [ ! -d "$KERNEL_HEADERS" ]; then
    echo "Error: Kernel headers not found at $KERNEL_HEADERS" >&2
    exit 1
fi
echo "Kernel headers found."

echo "==== Step 2: Compile the Driver ===="
if ! make -C "$KERNEL_HEADERS" M=$(pwd) modules; then
    echo "Error: Driver build failed." >&2
    exit 1
fi
echo "Driver compiled successfully."

echo "==== Step 3: Check for DRM Exports ===="
for symbol in drm_gem_fb_end_cpu_access mipi_dbi_command drm_fbdev_generic_setup; do
    if ! grep -q "$symbol" "$KERNEL_HEADERS/Module.symvers"; then
        echo "Error: Missing export for symbol $symbol" >&2
    else
        echo "Export found: $symbol"
    fi
done

echo "==== Step 4: Ensure Required Modules are Loaded ===="
for mod in "${DRM_MODULES[@]}"; do
    if ! lsmod | grep -q "$mod"; then
        echo "Loading $mod..."
        sudo modprobe "$mod"
    else
        echo "Module $mod is already loaded."
    fi
done

echo "==== Step 5: Check Kernel Configuration ===="
if [ -f "$KERNEL_HEADERS/.config" ]; then
    echo "Verifying CONFIG_DRM options..."
    grep CONFIG_DRM "$KERNEL_HEADERS/.config" | grep -v '^#'
else
    echo "Error: Kernel config file not found." >&2
fi

echo "==== Step 6: Insert the Module ===="
sudo rmmod "$MODULE_NAME" 2>/dev/null || echo "Module $MODULE_NAME not loaded, skipping removal."
if ! sudo insmod "$MODULE_FILE"; then
    echo "Error: Failed to insert module $MODULE_NAME." >&2
    dmesg | tail -n 20
    exit 1
fi
echo "Module $MODULE_NAME inserted successfully."

echo "==== Step 7: Verify Module Status ===="
lsmod | grep "$MODULE_NAME" && echo "Module $MODULE_NAME is loaded." || echo "Module $MODULE_NAME is not loaded."

echo "==== Step 8: DRM Debug Logs ===="
echo "Collecting DRM-related dmesg logs..."
dmesg | grep -i drm | tail -n 50

echo "==== Script Complete ===="
