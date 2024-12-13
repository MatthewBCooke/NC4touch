#!/bin/bash

# Update and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y git build-essential bc bison flex libssl-dev libncurses5-dev raspberrypi-kernel-headers device-tree-compiler
sudo apt install i2c-tools libi2c-dev
sudo apt install libgpiod-dev
sudo apt install gpiod

# Build and install the ILI9488 driver
cd /home/nc4/TouchscreenApparatus/src/lcd/ili9488
make
sudo cp ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
sudo depmod -a

# Set up device tree overlay
cd /home/nc4/TouchscreenApparatus/src/lcd/ili9488/rpi-overlays
sudo dtc -@ -I dts -O dtb -o /boot/overlays/ili-9488.dtbo ili-9488.dts

# Add configuration entries to /boot/firmware/config.txt
# This ensures the Raspberry Pi loads the correct overlay and parameters for the ILI9488 display.
# Prevents duplicate entries by checking if each line already exists in the file.
grep -qxF "dtoverlay=ili-9488-overlay" /boot/firmware/config.txt || echo "dtoverlay=ili-9488-overlay" | sudo tee -a /boot/firmware/config.txt
grep -qxF "dtparam=speed=62000000" /boot/firmware/config.txt || echo "dtparam=speed=62000000" | sudo tee -a /boot/firmware/config.txt
grep -qxF "dtparam=rotation=90" /boot/firmware/config.txt || echo "dtparam=rotation=90" | sudo tee -a /boot/firmware/config.txt

# Reboot
sudo reboot
