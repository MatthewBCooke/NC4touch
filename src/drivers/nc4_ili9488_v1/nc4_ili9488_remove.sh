echo "==== Uninstalling the nc4_ili9488 Driver ===="

# Unload the driver
echo "Unloading the driver..."
if sudo rmmod nc4_ili9488 || sudo modprobe -r nc4_ili9488; then
    echo "Driver unloaded successfully."
else
    echo "Warning: Failed to unload driver. It may not be loaded." >&2
fi

# Remove the driver file
echo "Removing the driver file..."
if sudo rm /lib/modules/$(uname -r)/extra/nc4_ili9488.ko; then
    echo "Driver file removed successfully."
else
    echo "Warning: Driver file not found or already removed." >&2
fi

# Remove compressed driver file if it exists
echo "Checking for compressed driver file..."
if [ -f /lib/modules/$(uname -r)/updates/nc4_ili9488.ko.xz ]; then
    if sudo rm /lib/modules/$(uname -r)/updates/nc4_ili9488.ko.xz; then
        echo "Compressed driver file removed successfully."
    else
        echo "Warning: Failed to remove compressed driver file." >&2
    fi
else
    echo "No compressed driver file found."
fi

# Update module dependencies
echo "Updating module dependencies..."
sudo depmod -a

# Unbind the device if still bound
echo "Unbinding SPI device if still bound..."
if echo "spi0.0" | sudo tee /sys/bus/spi/drivers/nc4_ili9488/unbind 2>/dev/null; then
    echo "Device spi0.0 unbound successfully."
else
    echo "No binding found for spi0.0."
fi

# Remove the overlay file
echo "Removing the overlay file..."
if sudo rm /boot/firmware/overlays/nc4_ili9488.dtbo; then
    echo "Overlay file removed successfully."
else
    echo "Warning: Overlay file not found or already removed." >&2
fi

# # Update /boot/firmware/config.txt
# echo "Updating /boot/firmware/config.txt..."
# if sudo sed -i '/dtoverlay=nc4_ili9488/d' /boot/firmware/config.txt && sudo sed -i '/dtdebug=on/d' /boot/firmware/config.txt; then
#     echo "Overlay references removed from /boot/firmware/config.txt."
# else
#     echo "Error: Failed to update /boot/firmware/config.txt." >&2
# fi

# Rebuild the initramfs (if required)
echo "Rebuilding the initramfs (if applicable)..."
sudo update-initramfs -u

# Verify the driver is not loaded
echo "Verifying the driver is not loaded..."
if lsmod | grep nc4_ili9488; then
    echo "Error: Driver is still loaded." >&2
else
    echo "Driver is no longer loaded."
fi

echo "Checking kernel logs for references..."
if dmesg | grep -i nc4_ili9488; then
    echo "Warning: Residual references found in kernel logs." >&2
else
    echo "No references found in kernel logs."
fi

echo "==== Verifying Removal ===="

# Check if the module is still available
echo "Checking if the module is still available..."
if sudo modinfo nc4_ili9488; then
    echo "Error: Module is still available." >&2
else
    echo "Module successfully removed."
fi

# Check for residual entries in /proc/device-tree
echo "Checking for residual entries in /proc/device-tree..."
if grep -ril 'nc4_ili9488' /proc/device-tree/; then
    echo "Warning: Residual entries found in /proc/device-tree." >&2
else
    echo "No residual entries found in /proc/device-tree."
fi

# Check for residual SPI driver bindings
echo "Checking for residual SPI driver bindings..."
if [ -d "/sys/bus/spi/devices/spi0.0" ]; then
    ls -l /sys/bus/spi/devices/spi0.0/driver || echo "No driver bound to spi0.0."
else
    echo "No spi0.0 device found."
fi

if [ -d "/sys/bus/spi/devices/spi0.1" ]; then
    ls -l /sys/bus/spi/devices/spi0.1/driver || echo "No driver bound to spi0.1."
else
    echo "No spi0.1 device found."
fi

# # Check for residual configurations in /boot
# echo "Searching for residual configurations in /boot..."
# grep -i 'nc4_ili9488' /boot/config.txt || echo "No nc4_ili9488 references in /boot/config.txt."
# grep -ril 'nc4_ili9488' /boot/ || echo "No residual files related to nc4_ili9488 in /boot."

# Confirm no residual modules in /lib/modules
echo "Checking for residual modules in /lib/modules..."
find /lib/modules/$(uname -r)/ -name '*nc4_ili9488*' || echo "No nc4_ili9488 modules found in /lib/modules."

# echo "==== Uninstallation Rebooting Now ===="
# sudo reboot
