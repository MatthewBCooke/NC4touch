#!/bin/bash
################################################################################
# validate.sh
#
# Purpose: Validate overlays, drivers, and devices post-boot.
################################################################################

# Configuration
OVERLAY_NAME="nc4_ili9488"
OVERLAY_DTBO="/boot/firmware/overlays/${OVERLAY_NAME}.dtbo"
DRIVER_NAME="nc4_ili9488"
DRIVER_PATH="/lib/modules/$(uname -r)/extra/${DRIVER_NAME}.ko"
LOG_FILE="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs/validation.log"
EXPECTED_NODES=("pitft0@0" "pitft0_pins" "pitft1@1" "pitft1_pins" "pitft2@2" "pitft2_pins" "backlight")

# Error Handling
set -e
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
> "$LOG_FILE"

# Function: Validate Overlay
validate_overlay() {
    echo "Validating overlay..." | tee -a "$LOG_FILE"
    if [[ -f "$OVERLAY_DTBO" ]]; then
        echo "Overlay file found: $OVERLAY_DTBO" | tee -a "$LOG_FILE"
    else
        echo "!!ERROR!!: Overlay file not found: $OVERLAY_DTBO" | tee -a "$LOG_FILE"
    fi

    # Check nodes in the device tree
    echo "Checking overlay nodes in the live device tree..." | tee -a "$LOG_FILE"
    for NODE in "${EXPECTED_NODES[@]}"; do
        if grep -q "$NODE" /proc/device-tree; then
            echo "Node '$NODE' is present in the device tree." | tee -a "$LOG_FILE"
        else
            echo "!!ERROR!!: Node '$NODE' not found in the device tree." | tee -a "$LOG_FILE"
        fi
    done

    # Check kernel logs
    echo "Checking kernel logs for overlay application..." | tee -a "$LOG_FILE"
    if dmesg | grep -qi "$OVERLAY_NAME"; then
        echo "Overlay is logged in kernel messages." | tee -a "$LOG_FILE"
    else
        echo "!!ERROR!!: Overlay not found in kernel messages." | tee -a "$LOG_FILE"
    fi

    # Validate config.txt
    echo "Verifying overlay references in config.txt..." | tee -a "$LOG_FILE"
    if grep -q "dtoverlay=$OVERLAY_NAME" /boot/config.txt; then
        echo "Overlay is referenced in config.txt." | tee -a "$LOG_FILE"
    else
        echo "!!ERROR!!: Overlay not found in config.txt." | tee -a "$LOG_FILE"
    fi
}

# Function: Validate Driver
validate_driver() {
    echo "Validating driver..." | tee -a "$LOG_FILE"
    if [[ -f "$DRIVER_PATH" ]]; then
        echo "Driver file found: $DRIVER_PATH" | tee -a "$LOG_FILE"
    else
        echo "!!ERROR!!: Driver file not found: $DRIVER_PATH" | tee -a "$LOG_FILE"
    fi

    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "Driver module is loaded." | tee -a "$LOG_FILE"
    else
        echo "!!ERROR!!: Driver module is not loaded." | tee -a "$LOG_FILE"
    fi
}

# Function: Validate Devices
validate_devices() {
    echo "Validating devices..." | tee -a "$LOG_FILE"

    # SPI Devices
    echo "Checking SPI devices..." | tee -a "$LOG_FILE"
    for DEVICE in /sys/bus/spi/devices/spi1.*; do
        if [[ -d "$DEVICE" ]]; then
            echo "SPI device found: $(basename "$DEVICE")" | tee -a "$LOG_FILE"
        else
            echo "!!ERROR!!: No SPI devices found." | tee -a "$LOG_FILE"
        fi
    done

    # DRM Nodes
    echo "Checking DRM nodes..." | tee -a "$LOG_FILE"
    if [[ -d /sys/class/drm/card0 ]]; then
        echo "DRM node /sys/class/drm/card0 is present." | tee -a "$LOG_FILE"
    else
        echo "!!ERROR!!: DRM node is missing." | tee -a "$LOG_FILE"
    fi

    # Framebuffers
    echo "Checking framebuffers..." | tee -a "$LOG_FILE"
    for FB in /dev/fb*; do
        if [[ -e "$FB" ]]; then
            echo "Framebuffer found: $FB" | tee -a "$LOG_FILE"
        else
            echo "!!ERROR!!: No framebuffers found." | tee -a "$LOG_FILE"
        fi
    done
}

# Function: Validate GPIO States
validate_gpio_states() {
    echo "Validating GPIO pin states..." | tee -a "$LOG_FILE"
    declare -A GPIO_LABELS=(
        [20]="MOSI"
        [21]="SCLK"
        [27]="Backlight"
        [18]="LCD_0 CS (CE0)"
        [25]="LCD_0 RES"
        [24]="LCD_0 DC"
        [17]="LCD_1 CS (CE1)"
        [23]="LCD_1 RES"
        [22]="LCD_1 DC"
        [16]="LCD_2 CS (CE2)"
        [13]="LCD_2 RES"
        [12]="LCD_2 DC"
    )
    for PIN in "${!GPIO_LABELS[@]}"; do
        echo "Checking GPIO $PIN (${GPIO_LABELS[$PIN]}):" | tee -a "$LOG_FILE"
        raspi-gpio get "$PIN" | tee -a "$LOG_FILE"
    done
}

# Main Execution
validate_overlay
validate_driver
validate_devices
validate_gpio_states

echo "Validation complete. Results are logged to $LOG_FILE."
