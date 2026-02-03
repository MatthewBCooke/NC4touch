
# 0. Add the overlay to config.txt
sudo nano /boot/firmware/config.txt
dtoverlay=test_overlay

# 0. CD to dirname
cd /home/nc4/TouchscreenApparatus/tests/test_overlay

# 2. Compile the overlay
dtc -@ -I dts -O dtb -o test_overlay.dtbo test_overlay.dts

# 3. Copy the compiled overlay to the overlays directory
sudo cp test_overlay.dtbo /boot/firmware/overlays/

# 4. Reboot to apply the overlay
sudo reboot

# All
cd /home/nc4/TouchscreenApparatus/tests/test_overlay
dtc -@ -I dts -O dtb -o test_overlay.dtbo test_overlay.dts
sudo cp test_overlay.dtbo /boot/firmware/overlays/
echo "dtoverlay=test_overlay" | sudo tee -a /boot/firmware/config.txt
sudo reboot




# 1. Check if the overlay is listed in the device tree
ls /proc/device-tree/overlays/test_overlay

# 2. Dump the device tree to verify the dummy node
dtc -I fs /proc/device-tree > active_device_tree.dts
grep -A 5 "test_node" active_device_tree.dts

# 3. Check kernel logs for overlay application
dmesg | grep -i overlay

# All
ls /proc/device-tree/overlays/test_overlay
dtc -I fs /proc/device-tree > active_device_tree.dts
grep -A 5 "test_node" active_device_tree.dts
dmesg | grep -i overlay




# 1. Remove the overlay from config.txt
sudo nano /boot/firmware/config.txt

# 2. Delete the overlay file
sudo rm /boot/firmware/overlays/test_overlay.dtbo

# 3. Reboot to remove the overlay from the active device tree
sudo reboot

# All
sudo sed -i '/dtoverlay=test_overlay/d' /boot/firmware/config.txt
sudo rm /boot/firmware/overlays/test_overlay.dtbo
sudo reboot