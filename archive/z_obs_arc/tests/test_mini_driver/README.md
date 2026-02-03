## Compile the Overlay
Create test_mini_overlay.dts in some folder, for example ~/overlays/.

Compile into a .dtbo:
```
cd /home/nc4/TouchscreenApparatus/tests/test_mini_driver
```
```
dtc -@ -I dts -O dtb -o test_mini_overlay.dtbo test_mini_overlay.dts
```

Copy it to your Pi’s overlay directory:
```
sudo cp test_mini_overlay.dtbo /boot/overlays/
```

Edit /boot/config.txt (or /boot/firmware/config.txt on some distros) to load your overlay at boot:
```
sudo nano /boot/firmware/config.txt
```
```
dtoverlay=test_mini_overlay
```

## Reboot to Load the Overlay
Reboot:
```
sudo reboot
```

After reboot, check logs:
```
 | grep -i 'test_mini'
```
You may see something like “(overlay) test_mini_overlay loaded successfully” if everything’s working.

Alternatively, you can inspect /proc/device-tree/soc/spi@7e204000 to see if test_mini@0 node is there:
```
ls /proc/device-tree/soc/spi@7e204000/
```
You should see a directory named test_mini@0.

## Build and Insert the Driver
Build the out-of-tree driver:
```
cd /home/nc4/TouchscreenApparatus/tests/test_mini_driver
```
```
make
```

This should produce test_mini_driver.ko.

## Insert the module:

### Install and Load with modprobe

Copy the .ko file to the system module directory:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
```
```
sudo cp test_mini_driver.ko /lib/modules/$(uname -r)/extra/
```

Update the module dependency database:
```
sudo depmod -a
```

Load the module by name using modprobe:
```
sudo modprobe test_mini_driver
```

Check if the module was successfully loaded:
```
dmesg | grep -i test_mini_driver
```


## Varify with driver loaded

Check if the Device Node Exists After Boot indicating overlay loaded
```
ls /proc/device-tree/soc/spi@7e204000/
```
You should see a directory named test_mini@0.

Check if the Driver is Loaded:
```
lsmod | grep test_mini
```
Should see:
```
test_mini_driver       12288  0
```

Verify the Kernel Logs for Driver Activity
```
dmesg | grep -i test_mini
```
If the overlay node is found, the driver’s probe() function logs “Probed! (dev=spi0.0).”

Check logs:
```
dmesg | grep -i 'test_mini'
```
If the overlay node is found, the driver’s probe() function logs “Probed! (dev=spi0.0).”


(Optional) Remove the module to test the remove() function:
```
sudo rmmod test_mini_driver
```
```
dmesg | grep -i 'test_mini'
```
You’ll see “Removed!” if it’s removed cleanly.
