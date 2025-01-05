# Compile and copy nc4_ili9488.dtbo to /boot/firmware/overlays/nc4_ili9488.dtbo":
dtc -@ -I dts -O dtb -o /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dtbo /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dts
sudo cp /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dtbo "/boot/firmware/overlays/nc4_ili9488.dtbo"
ls -l /boot/firmware/overlays/nc4_ili9488.dtbo

# Apply the Device Tree Overlay to the running system and extract logs
sudo dtoverlay nc4_ili9488
dmesg | grep -i "overlay\|dtdebug\|spi\|ili9488" > /home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug/dmesg_overlay.txt

# ALL
dtc -@ -I dts -O dtb -o /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dtbo /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dts
sudo cp /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dtbo "/boot/firmware/overlays/nc4_ili9488.dtbo"
sudo dtoverlay nc4_ili9488
dmesg | grep -i "overlay\|dtdebug\|spi\|ili9488" > /home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug/dmesg_overlay.txt

# Decompile a Device Tree Blob (.dtbo) file back into a Device Tree Source (.dts) file for inspection
sudo dtc -I dtb -O dts -o /home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug/nc4_ili9488_decompiled.dts /boot/firmware/overlays/nc4_ili9488.dtbo




# Delete dtbo
sudo rm /boot/firmware/overlays/nc4_ili9488.dtbo


# Decompile base DT
sudo dtc -I fs -O dts -o /home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug/nc4_ili9488_decompiled.dts /proc/device-tree
