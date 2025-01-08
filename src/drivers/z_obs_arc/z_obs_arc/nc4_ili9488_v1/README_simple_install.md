## Compile the Overlay

Compile into a .dtbo:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```
```
dtc -@ -I dts -O dtb -o nc4_ili9488.dtbo nc4_ili9488-overlay.dts
```

Copy it to your Pi’s overlay directory:
```
sudo cp nc4_ili9488.dtbo /boot/overlays/
```

Edit /boot/config.txt (or /boot/firmware/config.txt on some distros) to load your overlay at boot:
```
sudo nano /boot/firmware/config.txt
```
```
dtoverlay=nc4_ili9488
```

## Reboot to Load the Overlay
Reboot:
```
sudo reboot
```

After reboot, check logs:
```
dmesg | grep -i 'nc4_ili9488'
```
You may see something like “(overlay) nc4_ili9488 loaded successfully” if everything’s working.

Alternatively, you can inspect /proc/device-tree/soc/spi@7e204000 to see if nc4_ili9488@0 node is there:
```
ls /proc/device-tree/soc/spi@7e204000/
```
You should see a directory named nc4_ili9488@0.

## Build and Insert the Driver
Build the out-of-tree driver:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```
```
make
```
This should produce nc4_ili9488.ko.

## Insert the module:

### Install and Load with modprobe

Copy the .ko file to the system module directory:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
```
```
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
```

Update the module dependency database:
```
sudo depmod -a
```

Load the module by name using modprobe:
```
sudo modprobe nc4_ili9488
```

Check if the module was successfully loaded:
```
dmesg | grep -i nc4_ili9488
```

Reboot:
```
sudo reboot
```


## Varify with driver loaded

Check if the Device Node Exists After Boot indicating overlay loaded
```
ls /proc/device-tree/soc/spi@7e204000/
```
You should see a directory named nc4_ili9488@0.

Check if the Driver is Loaded:
```
lsmod | grep nc4_ili9488
```
Should see:
```
nc4_ili9488       12288  0
```

Verify the Kernel Logs for Driver Activity
```
dmesg | grep -i nc4_ili9488
```
If the overlay node is found, the driver’s probe() function logs “Probed! (dev=spi0.0).”

Check logs:
```
dmesg | grep -i 'nc4_ili9488'
```
If the overlay node is found, the driver’s probe() function logs “Probed! (dev=spi0.0).”

If the overlay does not seemto have loaded applying it manually and checking for errors:
```
sudo dtoverlay -v nc4_ili9488
```


## Check for SPI 
```
ls /dev/spi*
```

## Check active frame buffers
```
ls /dev/fb*
```

## Draw an image to the fb0 buffer:
```
sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/A01.bmp
```