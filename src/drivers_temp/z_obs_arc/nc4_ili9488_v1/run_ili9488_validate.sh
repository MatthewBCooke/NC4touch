#!/bin/bash

OVERLAY_NAME="nc4_ili9488"
OVERLAY_DTBO="/boot/firmware/overlays/${OVERLAY_NAME}.dtbo"
DRIVER_NAME="nc4_ili9488"
DRIVER_PATH="/lib/modules/$(uname -r)/extra/${DRIVER_NAME}.ko"
LOG_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs"
LOG_FILE="${LOG_DIR}/install_validation.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Redirect all output to log file and console
exec > >(tee -a "$LOG_FILE") 2>&1
echo "Logging script output to $LOG_FILE"

echo "=== Starting Overlay and Driver Validation ===" | tee -a "$LOG_FILE"

## Validate Overlay
echo "==== Validating Overlay ====" | tee -a "$LOG_FILE"

# Check if overlay .dtbo exists
if [ -f "$OVERLAY_DTBO" ]; then
    echo "Overlay file found: $OVERLAY_DTBO" | tee -a "$LOG_FILE"
else
    echo "Error: Overlay file not found: $OVERLAY_DTBO" | tee -a "$LOG_FILE" >&2
    exit 1
fi

# Define the expected nodes
EXPECTED_NODES=("panel0" "panel1" "pitft0" "pitft1" "pitft0@0" "pitft1@1" "pitft_pins_0" "pitft_pins_1" "backlight")

# Validate each node
echo "Checking overlay nodes in the device tree..." | tee -a "$LOG_FILE"
for NODE in "${EXPECTED_NODES[@]}"; do
    if dtc -I fs /proc/device-tree | grep -q "$NODE"; then
        echo "Node '$NODE' found in the flattened device tree." | tee -a "$LOG_FILE"
    else
        echo "Node '$NODE' not found. Check overlay or binding for issues." | tee -a "$LOG_FILE"
    fi
done

# List all nodes under the SPI bus for detailed inspection
SPI_BUS_PATH="/proc/device-tree/soc/spi@7e204000"
if [ -d "$SPI_BUS_PATH" ]; then
    echo "Listing all nodes under $SPI_BUS_PATH for verification:" | tee -a "$LOG_FILE"
    ls "$SPI_BUS_PATH" | tee -a "$LOG_FILE"
else
    echo "SPI bus path $SPI_BUS_PATH not found. Check overlay or hardware configuration." | tee -a "$LOG_FILE"
fi

# Check kernel logs for overlay application
echo "Checking kernel logs for overlay application..." | tee -a "$LOG_FILE"
if dmesg | grep -qi "$OVERLAY_NAME"; then
    echo "Overlay is logged in kernel messages." | tee -a "$LOG_FILE"
else
    echo "Overlay not found in kernel messages. Check the logs for issues." | tee -a "$LOG_FILE"
fi

# Verify overlay entries in config.txt
echo "Verifying overlay references in config.txt..." | tee -a "$LOG_FILE"
if grep -q "dtoverlay=$OVERLAY_NAME" /boot/firmware/config.txt; then
    echo "Overlay is referenced in config.txt." | tee -a "$LOG_FILE"
else
    echo "Overlay not found in config.txt. Ensure it is added correctly." | tee -a "$LOG_FILE"
fi

# Debugging overlay issues
echo "Debugging overlay loading (if issues persist)..." | tee -a "$LOG_FILE"
dmesg | grep -Ei 'overlay|dtoverlay|firmware|dt' | tee -a "$LOG_FILE"

# Check frame buffer devices
echo "Checking active frame buffer devices..." | tee -a "$LOG_FILE"
if ls /dev/fb* 1>/dev/null 2>&1; then
    echo "Frame buffer devices found: $(ls /dev/fb*)" | tee -a "$LOG_FILE"
else
    echo "No frame buffer devices found. Overlay may not be fully functional." | tee -a "$LOG_FILE"
fi

# Validate the .dtbo file
echo "Validating the .dtbo file syntax..." | tee -a "$LOG_FILE"
if sudo dtc -I dtb -O dts -o /dev/null "$OVERLAY_DTBO" 2>/dev/null; then
    echo ".dtbo file is valid." | tee -a "$LOG_FILE"
else
    echo "Error: .dtbo file contains syntax issues." | tee -a "$LOG_FILE" >&2
    exit 1
fi

## Validate Driver
echo "==== Validating Driver ====" | tee -a "$LOG_FILE"

# Check if the driver module exists
if [ -f "$DRIVER_PATH" ]; then
    echo "Driver file found: $DRIVER_PATH" | tee -a "$LOG_FILE"
else
    echo "Error: Driver file not found: $DRIVER_PATH" | tee -a "$LOG_FILE" >&2
    exit 1
fi

# Check if the module is loaded
echo "Checking if the driver module is loaded..." | tee -a "$LOG_FILE"
if lsmod | grep -q "$DRIVER_NAME"; then
    echo "Driver module is loaded." | tee -a "$LOG_FILE"
else
    echo "Driver module is not loaded. Attempting to load it..." | tee -a "$LOG_FILE"
    sudo insmod "$DRIVER_PATH"
    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "Driver module loaded successfully." | tee -a "$LOG_FILE"
    else
        echo "Error: Failed to load the driver module." | tee -a "$LOG_FILE" >&2
        exit 1
    fi
fi

# Final kernel log check
echo "Final kernel logs:" | tee -a "$LOG_FILE"
dmesg | grep -i "$DRIVER_NAME" | tee -a "$LOG_FILE"

echo "=== Validation Complete ===" | tee -a "$LOG_FILE"
