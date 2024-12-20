#!/bin/bash
# ./setup.sh

# Function to check if a package is installed
is_package_installed() {
    dpkg -l | grep -qw "$1"
}

# Function to check if a Python library is installed
is_python_lib_installed() {
    python3 -c "import $1" &> /dev/null
}

# Function to add an entry to the config file if it doesn't already exist
add_to_config() {
    local entry="$1"
    local file="$CONFIG_FILE"

    if grep -qxF "$entry" "$file"; then
        echo "Entry '$entry' already exists in $file."
    else
        echo "Adding entry: $entry"
        echo "$entry" | sudo tee -a "$file" > /dev/null
    fi
}

echo "==== Updating System and Installing Dependencies ===="
sudo apt update && sudo apt upgrade -y

# System libraries
declare -a SYSTEM_PACKAGES=(
    "git"
    "build-essential"
    "bc"
    "bison"
    "flex"
    "libssl-dev"
    "libncurses5-dev"
    "raspberrypi-kernel-headers"
    "device-tree-compiler"
    "i2c-tools"
    "libi2c-dev"
    "libgpiod-dev"
    "gpiod"
    "pigpio"  
)

for package in "${SYSTEM_PACKAGES[@]}"; do
    if is_package_installed "$package"; then
        echo "Package '$package' is already installed."
    else
        echo "Installing package: $package"
        sudo apt install -y "$package"
    fi
done

echo "==== Checking and Installing Python Libraries ===="
# Python libraries
declare -a PYTHON_LIBRARIES=("gpiod" "numpy")

for lib in "${PYTHON_LIBRARIES[@]}"; do
    if is_python_lib_installed "$lib"; then
        echo "Python library '$lib' is already installed."
    else
        echo "Installing Python library: $lib"
        python3 -m pip install "$lib"
    fi
done

echo "==== Building and Installing the ILI9488 Driver ===="
# Build and install the ILI9488 driver

# Perform a clean build
ILI9488_DIR="/home/nc4/TouchscreenApparatus/src/drivers/ili9488"
cd "$ILI9488_DIR"
echo "Cleaning previous build..."
make clean || true              # Ignore errors if no previous build exists
echo "Building driver..."
make
echo "Installing driver..."
sudo cp ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
sudo depmod -a
echo "Driver successfully built and installed."
echo "Rebuild the Initramfs..."
sudo update-initramfs -u

echo "==== Setting Up Device Tree Overlay ===="
# Compile and install the device tree overlay
DT_OVERLAY_DIR="/home/nc4/TouchscreenApparatus/src/drivers/ili9488/rpi-overlays"
cd /home/nc4/TouchscreenApparatus/src/drivers/ili9488/rpi-overlays
sudo dtc -@ -I dts -O dtb -o /boot/overlays/ili9488.dtbo ili9488.dts

# echo "==== Adding Configuration to /boot/firmware/config.txt ===="
# # Add necessary configuration entries
# add_to_config "dtoverlay=ili9488"
# add_to_config "dtparam=speed=62000000"
# add_to_config "dtparam=rotation=90"

echo "==== Setup Complete. Rebooting Now ===="
sudo reboot
