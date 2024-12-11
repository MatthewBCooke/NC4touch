#!/bin/bash

# Update and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y git build-essential bc bison flex libssl-dev libncurses5-dev raspberrypi-kernel-headers device-tree-compiler

# Build and install the ILI9488 driver
cd src/lcd/ili9488
make
sudo cp ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
sudo depmod -a

# Set up device tree overlay
cd /home/nc4/TouchscreenApparatus/src/lcd/ili9488/rpi-overlays
sudo dtc -@ -I dts -O dtb -o /boot/overlays/ili-9488.dtbo ili-9488.dts
echo "dtoverlay=ili-9488-overlay" | sudo tee -a /boot/config.txt
echo "dtparam=speed=62000000" | sudo tee -a /boot/config.txt
echo "dtparam=rotation=90" | sudo tee -a /boot/config.txt

# Reboot
sudo reboot
