#!/bin/bash

# Configuration
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

echo "=== Starting Overlay and Driver Validation ==="

## Validate Overlay
echo "==== Validating Overlay ===="

# Check if overlay .dtbo exists
if [ -f "$OVERLAY_DTBO" ]; then
    echo "Overlay file found: $OVERLAY_DTBO"
else
    echo "Error: Overlay file not found: $OVERLAY_DTBO" >&2
    exit 1
fi

##############################################################################
# Capture and filter dtc warnings from the live device tree
##############################################################################
TMP_DTC_RAW="/tmp/dtc_raw_output.txt"
TMP_DTC_FILTERED="/tmp/dtc_filtered_output.txt"

# Run dtc on the live device tree, capturing *all* stderr to TMP_DTC_RAW
dtc -I fs /proc/device-tree 2> "$TMP_DTC_RAW" > /dev/null

# Filter out known Raspberry Pi "noise" warnings.
grep -vE '(unit_address_vs_reg|simple_bus_reg|avoid_default_addr_size|avoid_unnecessary_addr_size|unique_unit_address|clocks_property|power_domains_property|resets_property|gpios_property|interrupt_provider|dmas_property|msi_parent_property|phys_property|thermal_sensors_property)' \
    "$TMP_DTC_RAW" > "$TMP_DTC_FILTERED"

# Print or log the filtered dtc output
echo "---- Filtered dtc Warnings & Errors (non-RPi-specific) ----"
cat "$TMP_DTC_FILTERED"
echo "-----------------------------------------------------------"
echo "Note: Full dtc output (including Pi-specific warnings) is in $TMP_DTC_RAW"
echo

# Define the expected nodes
EXPECTED_NODES=(
    "pitft0@0"
    "pitft0_pins"
    "pitft1@1"
    "pitft1_pins"
    "backlight"
)

# Validate each node in the live device tree
echo "Checking overlay nodes in the live device tree..."
for NODE in "${EXPECTED_NODES[@]}"; do
    NODE_PATH="/proc/device-tree/soc/spi@7e204000/$NODE"
    if [ -d "$NODE_PATH" ] || grep -q "$NODE" "$TMP_DTC_RAW"; then
        echo "Node '$NODE' found in the live device tree."
    else
        echo "ERROR!! Node '$NODE' not found. Check overlay or binding for issues."
    fi
done

# List all nodes under the SPI bus for detailed inspection
SPI_BUS_PATH="/proc/device-tree/soc/spi@7e204000"
if [ -d "$SPI_BUS_PATH" ]; then
    echo "Listing all nodes under $SPI_BUS_PATH for verification:"
    ls "$SPI_BUS_PATH"
else
    echo "SPI bus path $SPI_BUS_PATH not found. Check overlay or hardware configuration."
fi

# Check kernel logs for overlay application
echo "Checking kernel logs for overlay application..."
if dmesg | grep -qi "$OVERLAY_NAME"; then
    echo "Overlay is logged in kernel messages."
else
    echo "Overlay not found in kernel messages. Check the logs for issues."
fi

# Verify overlay entries in config.txt
echo "Verifying overlay references in config.txt..."
if grep -q "dtoverlay=$OVERLAY_NAME" /boot/firmware/config.txt; then
    echo "Overlay is referenced in config.txt."
else
    echo "Overlay not found in config.txt. Ensure it is added correctly."
fi

## Validate Driver
echo "==== Validating Driver ===="

# Log and print dmesg output for the driver
echo "Fetching and logging dmesg output for $DRIVER_NAME..."
dmesg | grep "$DRIVER_NAME" | tee -a "$LOG_FILE"

# Check if the driver module exists
if [ -f "$DRIVER_PATH" ]; then
    echo "Driver file found: $DRIVER_PATH"
else
    echo "Error: Driver file not found: $DRIVER_PATH" >&2
    exit 1
fi

# Check if the module is loaded
echo "Checking if the driver module is loaded..."
if lsmod | grep -q "$DRIVER_NAME"; then
    echo "Driver module is loaded."
else
    echo "Driver module is not loaded. Attempting to load it..."
    sudo insmod "$DRIVER_PATH"
    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "Driver module loaded successfully."
    else
        echo "Error: Failed to load the driver module." >&2
        exit 1
    fi
fi

echo "=== Validation Complete ==="
