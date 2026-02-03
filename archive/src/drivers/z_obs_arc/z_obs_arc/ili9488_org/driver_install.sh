
echo "==== Setting Up Device Tree Overlay ===="
# Compile and install the device tree overlay
DT_OVERLAY_DIR="/home/nc4/TouchscreenApparatus/src/drivers/z_obs_arc/ili9488"
cd "$DT_OVERLAY_DIR"
sudo dtc -@ -I dts -O dtb -o /boot/firmware/overlays/ili9488.dtbo ili9488.dts

echo "==== Building and Installing the ILI9488 Driver ===="
# Build and install the ILI9488 driver
ILI9488_DIR="/home/nc4/TouchscreenApparatus/src/drivers/z_obs_arc/ili9488"
cd "$ILI9488_DIR"
echo "Cleaning previous build..."
make clean || true              # Ignore errors if no previous build exists
echo "Building driver..."
make
echo "Installing driver..."
# sudo mkdir -p /lib/modules/$(uname -r)/extra
# sudo cp ili9488.ko /lib/modules/$(uname -r)/extra/
sudo mkdir -p /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny
sudo cp ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
sudo depmod -a $(uname -r)
echo "Driver successfully built and installed."
#echo "Rebuild the Initramfs..."
#sudo update-initramfs -u

#echo "==== Setup Complete. Rebooting Now ===="
#sudo reboot