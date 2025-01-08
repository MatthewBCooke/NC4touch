#!/bin/bash
################################################################################
# install.sh
#
# Purpose: Compile and install the nc4_ili9488 overlay and driver on a 
# Raspberry Pi running Debian Bookworm.
################################################################################

# Load configuration
source /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/config.env

# Error handling
set -e
trap 'echo "!!ERROR!!: Script failed at line $LINENO."; exit 1;' ERR

# Functions
build_overlay() {
    echo "Building overlay..."
    dtc -@ -I dts -O dtb -o "$BUILDS_DIR/nc4_ili9488.dtbo" "$BASE_DIR/nc4_ili9488.dts"
    if [[ ! -f "$BUILDS_DIR/nc4_ili9488.dtbo" ]]; then
        echo "!!ERROR!!: Overlay compilation failed." >&2
        exit 1
    fi
    echo "Overlay compiled successfully."
}

install_overlay() {
    echo "Installing overlay..."
    sudo cp "$BUILDS_DIR/nc4_ili9488.dtbo" "/boot/firmware/overlays/nc4_ili9488.dtbo"
    if [[ $? -ne 0 ]]; then
        echo "!!ERROR!!: Failed to copy overlay." >&2
        exit 1
    fi
    echo "Overlay installed successfully."
}

build_driver() {
    echo "Building driver..."
    make clean -C "$BASE_DIR" || true
    make -C "$BASE_DIR"
    if [[ ! -f "$BUILDS_DIR/nc4_ili9488.ko" ]]; then
        echo "!!ERROR!!: Driver compilation failed." >&2
        exit 1
    fi
    echo "Driver compiled successfully."
}

install_driver() {
    echo "Installing driver..."
    sudo cp "$BUILDS_DIR/nc4_ili9488.ko" "/lib/modules/$(uname -r)/extra/"
    sudo depmod -a
    if [[ $? -ne 0 ]]; then
        echo "!!ERROR!!: Failed to install driver." >&2
        exit 1
    fi
    echo "Driver installed successfully."
}

validate_installation() {
    echo "Validating installation..."
    if ! lsmod | grep -q "nc4_ili9488"; then
        echo "!!ERROR!!: Driver not loaded. Attempting to load driver..."
        sudo modprobe nc4_ili9488 || { echo "!!ERROR!!: Failed to load driver." >&2; exit 1; }
    else
        echo "Driver is loaded successfully."
    fi
    if ! grep -q "dtoverlay=nc4_ili9488" /boot/config.txt; then
        echo "Adding overlay to /boot/config.txt..."
        echo "dtoverlay=nc4_ili9488" | sudo tee -a /boot/config.txt > /dev/null
    else
        echo "Overlay is already configured in /boot/config.txt."
    fi
    echo "Validation complete."
}

capture_logs() {
    echo "Capturing logs for validation..."
    LOG_FILE="$LOGS_DIR/installation_validation.log"
    mkdir -p "$LOGS_DIR"
    > "$LOG_FILE"
    sudo dmesg | grep "nc4_ili9488" >> "$LOG_FILE"
    if [[ -s "$LOG_FILE" ]]; then
        echo "Logs captured successfully. Logs saved to $LOG_FILE."
    else
        echo "No relevant logs found. Log file is empty." >&2
    fi
}

post_boot_validation() {
    echo "Performing post-boot validation..."
    if [[ -c /dev/spidev0.0 ]] && [[ -c /dev/spidev0.1 ]]; then
        echo "SPI devices are present: /dev/spidev0.0 and /dev/spidev0.1."
    else
        echo "!!ERROR!!: SPI devices are missing." >&2
        exit 1
    fi
    if [[ -d /sys/class/drm/card0 ]]; then
        echo "DRM node /sys/class/drm/card0 is present."
    else
        echo "!!ERROR!!: DRM node /sys/class/drm/card0 is missing." >&2
        exit 1
    fi
    echo "Post-boot validation completed successfully."
}

# Main Execution
build_overlay
install_overlay
build_driver
install_driver
validate_installation
capture_logs
post_boot_validation

echo "Installation, validation, and log capture complete. The system is ready. Please reboot to apply changes."
