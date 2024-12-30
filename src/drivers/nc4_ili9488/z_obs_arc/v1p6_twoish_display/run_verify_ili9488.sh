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

# Delete the old log file if it exists
if [[ -f "$LOG_FILE" ]]; then
    rm "$LOG_FILE"
fi

# Redirect all output to log file and console
exec > >(tee -a "$LOG_FILE") 2>&1
echo "Logging script output to $LOG_FILE"

echo
echo
echo "=== Starting Overlay and Driver Validation ==="

## Validate Overlay
echo
echo "==== Validating Overlay ===="
echo

# Check if overlay .dtbo exists
if [ -f "$OVERLAY_DTBO" ]; then
    echo "Overlay file found: $OVERLAY_DTBO"
else
    echo "!!ERROR!!: Overlay file not found: $OVERLAY_DTBO" >&2
    #exit 1
fi

# Capture and filter dtc warnings from the live device tree
TMP_DTC_RAW="/tmp/dtc_raw_output.txt"
TMP_DTC_FILTERED="/tmp/dtc_filtered_output.txt"

# Run dtc on the live device tree, capturing *all* stderr to TMP_DTC_RAW
dtc -I fs /proc/device-tree 2> "$TMP_DTC_RAW" > /dev/null

# Filter out known Raspberry Pi "noise" warnings.
grep -vE '(unit_address_vs_reg|simple_bus_reg|avoid_default_addr_size|avoid_unnecessary_addr_size|unique_unit_address|clocks_property|power_domains_property|resets_property|gpios_property|interrupt_provider|dmas_property|msi_parent_property|phys_property|thermal_sensors_property)' \
    "$TMP_DTC_RAW" > "$TMP_DTC_FILTERED"

# Print or log the filtered dtc output
echo
echo "---- Filtered dtc Warnings & Errors (non-RPi-specific) ----"
cat "$TMP_DTC_FILTERED"
echo "-----------------------------------------------------------"
echo "Note: Full dtc output (including Pi-specific warnings) is in $TMP_DTC_RAW"

# Define the expected nodes
EXPECTED_NODES=(
    "pitft0@0"
    "pitft0_pins"
    "pitft1@1"
    "pitft1_pins"
    "backlight"
)

# Validate each node in the live device tree
echo
echo "---- Checking overlay nodes in the live device tree ----"
for NODE in "${EXPECTED_NODES[@]}"; do
    NODE_PATHS=(
        "/proc/device-tree/soc/spi@7e204000/$NODE"
        "/proc/device-tree/soc/gpio@7e200000/$NODE"
    )
    
    FOUND=false
    for NODE_PATH in "${NODE_PATHS[@]}"; do
        if [ -d "$NODE_PATH" ]; then
            echo "Node '$NODE' found at path: $NODE_PATH"
            FOUND=true
            break
        fi
    done
    
    if ! $FOUND && grep -q "$NODE" "$TMP_DTC_RAW"; then
        echo "Node '$NODE' found in decompiled Device Tree (TMP_DTC_RAW)."
        FOUND=true
    fi

    if ! $FOUND; then
        echo "!!ERROR!!: Node '$NODE' not found. Check overlay or binding for issues."
    fi
done
echo "-----------------------------------------------------------"

# List all nodes under the SPI bus for detailed inspection
SPI_BUS_PATH="/proc/device-tree/soc/spi@7e204000"
echo
if [ -d "$SPI_BUS_PATH" ]; then
    echo "---- Listing all nodes under $SPI_BUS_PATH for verification: ----"
    ls "$SPI_BUS_PATH"
    echo "-----------------------------------------------------------"
else
    echo "SPI bus path $SPI_BUS_PATH not found. Check overlay or hardware configuration."
fi

# Check kernel logs for overlay application
echo
echo "Checking kernel logs for overlay application:"
if dmesg | grep -qi "$OVERLAY_NAME"; then
    echo "Overlay is logged in kernel messages."
else
    echo "Overlay not found in kernel messages. Check the logs for issues."
fi

# Verify overlay entries in config.txt
echo
echo "Verifying overlay references in config.txt:"
if grep -q "dtoverlay=$OVERLAY_NAME" /boot/firmware/config.txt; then
    echo "Overlay is referenced in config.txt."
else
    echo "Overlay not found in config.txt. Ensure it is added correctly."
fi

## Validate Driver
echo
echo "==== Validating Driver ===="
echo

# Check if the driver module exists
echo "Checking if the driver is found:"
if [ -f "$DRIVER_PATH" ]; then
    echo "Driver file found: $DRIVER_PATH"
else
    echo "!!ERROR!!: Driver file not found: $DRIVER_PATH" >&2
    #exit 1
fi

# Check if the module is loaded
echo
echo "Checking if the driver module is loaded:"
if lsmod | grep -q "$DRIVER_NAME"; then
    echo "Driver module is loaded."
else
    echo "Driver module is not loaded. Attempting to load it..."
    sudo insmod "$DRIVER_PATH"
    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "Driver module loaded successfully."
    else
        echo "!!ERROR!!: Failed to load the driver module." >&2
        #exit 1
    fi
fi

# Confirm the DRM cards setup
echo
echo "==== Verifying DRM Cards Setup ===="
echo
DRM_PATH="/sys/class/drm"
if [ -d "$DRM_PATH" ]; then
    echo "---- Listing DRM cards and connectors ----"
    ls "$DRM_PATH"
    echo
    echo "---- Details for each DRM card ----"
    for CARD in "$DRM_PATH"/card*; do
        echo "Inspecting $(basename "$CARD"):"
        ls "$CARD"
        if [ -f "$CARD/uevent" ]; then
            cat "$CARD/uevent"
        fi
        echo
    done
    echo "-----------------------------------------------------------"
else
    echo "!!ERROR!!: DRM path $DRM_PATH not found. Check driver setup."
fi

# Confirm framebuffers are associated with DRM cards
echo
echo "==== Verifying Framebuffers ===="
echo
FB_PATH="/sys/class/graphics"
if [ -d "$FB_PATH" ]; then
    echo "---- Listing framebuffers ----"
    ls "$FB_PATH"
    echo
    echo "---- Details for each framebuffer ----"
    for FB in "$FB_PATH"/fb*; do
        echo "Inspecting $(basename "$FB"):"
        ls "$FB"
        if [ -f "$FB/uevent" ]; then
            cat "$FB/uevent"
        fi
        echo
    done
    echo "-----------------------------------------------------------"
else
    echo "!!ERROR!!: Framebuffer path $FB_PATH not found. Check graphics setup."
fi

echo
echo "==== Checking Driver Probe and Device Binding for SPI Devices ===="

# Check for spi0.0
if dmesg | grep -q -i "nc4_ili9488.*spi0.0"; then
    echo "Driver probe for spi0.0 detected in logs."
else
    echo "!!ERROR!!: No logs found for driver probe on spi0.0."
fi

if [ -e /sys/bus/spi/devices/spi0.0/driver ]; then
    DRIVER_PATH=$(readlink /sys/bus/spi/devices/spi0.0/driver)
    if [[ $DRIVER_PATH == *"nc4_ili9488"* ]]; then
        echo "spi0.0 is correctly bound to nc4_ili9488 driver."
    else
        echo "!!ERROR!!: spi0.0 is not bound to nc4_ili9488 driver."
    fi
else
    echo "!!ERROR!!: No driver found bound to spi0.0."
fi

# Check for spi0.1
if dmesg | grep -q -i "nc4_ili9488.*spi0.1"; then
    echo "Driver probe for spi0.1 detected in logs."
else
    echo "!!ERROR!!: No logs found for driver probe on spi0.1."
fi

if [ -e /sys/bus/spi/devices/spi0.1/driver ]; then
    DRIVER_PATH=$(readlink /sys/bus/spi/devices/spi0.1/driver)
    if [[ $DRIVER_PATH == *"nc4_ili9488"* ]]; then
        echo "spi0.1 is correctly bound to nc4_ili9488 driver."
    else
        echo "!!ERROR!!: spi0.1 is not bound to nc4_ili9488 driver."
    fi
else
    echo "!!ERROR!!: No driver found bound to spi0.1."
fi


# Validate GPIO Pin States
echo
echo "==== Validating GPIO Pin States ===="
echo
GPIO_PINS=(7 8 18 23 24 25)
for PIN in "${GPIO_PINS[@]}"; do
    echo "Checking GPIO $PIN:"
    raspi-gpio get $PIN
done

# # Log and print relevant dmesg output for debugging
# echo
# echo "==== Fetching and logging dmesg output (nc4_ili9488, SPI, GPIO, and DTB) ==== "
# dmesg | grep -E "nc4_ili9488|spi|gpio|dtb" | tee -a "$LOG_FILE"

echo
echo "=== Validation Complete ==="
