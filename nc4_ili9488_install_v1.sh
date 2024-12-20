echo "==== Setting Up Device Tree Overlay ===="
# Compile and install the device tree overlay
DT_OVERLAY_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/rpi-overlays"
cd "$DT_OVERLAY_DIR"
sudo dtc -@ -I dts -O dtb -o /boot/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts

echo "==== Building and Installing the ILI9488 Driver ===="
# Build and install the ILI9488 driver
ILI9488_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488"
cd "$ILI9488_DIR"
echo "Cleaning previous build..."
make clean || true             
echo "Building driver..."
make
echo "Installing driver..."
sudo mkdir -p /lib/modules/$(uname -r)/extra/
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a
modinfo nc4_ili9488
echo "Driver successfully built and installed."
echo "Rebuild the Initramfs..."
sudo update-initramfs -u

echo "==== Setup Complete. Rebooting Now ===="
sudo reboot