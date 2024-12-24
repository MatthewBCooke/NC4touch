# Instructions to build, install, and test the nc4_ili9488 driver.

## System setup

### Make sure you have installed kernel headers and build tools:
```
sudo apt-get update
```
```
sudo apt-get install build-essential git bc bison flex libssl-dev -y
```
The "fbi" tool is used for testing by showing images on the framebuffer.
```
sudo apt-get install device-tree-compiler -y
```


### installing the needed DRM modules from the kernel source

Install the tools needed to build kernel modules and DRM support.
```
sudo apt-get update && sudo apt-get upgrade -y
```
```
sudo apt-get install build-essential git bc bison flex libssl-dev \
    libncurses-dev raspberrypi-kernel-headers -y
```

Download the kernel source to a dedicated directory.
```
git clone --depth=1 https://github.com/raspberrypi/linux ~/linux
cd ~/linux
```

Set up the kernel configuration for Raspberry Pi.
```
make bcm2711_defconfig
```

Generate required files (e.g., Module.symvers) for building modules.
```
make modules_prepare -j$(nproc)
```


Compile only the DRM-related kernel modules for faster builds.
```
make M=drivers/gpu/drm modules -j$(nproc)
```

Install the newly built DRM modules into the current system.
```
sudo make M=drivers/gpu/drm modules_install
sudo depmod -a
```

Load the required DRM modules into the running kernel.
```
sudo modprobe drm
sudo modprobe drm_kms_helper
sudo modprobe drm_gem_dma_helper
```

Check if the modules are loaded and available.
```
lsmod | grep drm
```

### Install Raspberry Pi kernel configured for the BCM2711 architecture

Clone the Raspberry Pi kernel source:
```
git clone --depth=1 https://github.com/raspberrypi/linux
```
```
cd linux
```

Configure the kernel for Raspberry Pi:
```
make bcm2711_defconfig
```

Prepared the kernel build environment:
```
make modules_prepare
```

Build the entire kernel environment to ensure all dependencies and metadata:
```
make -j$(nproc)
```

Confirmed `Module.symvers` was created:
```
ls ~/linux/Module.symvers
```

Verify DRM subsystem object files were compiled:
```
find ~/linux/drivers/gpu/drm -name '*.o'
```

Set up kernel source directory:
```
cd /home/nc4/linux
```

Configure the kernel modules installation:
```
sudo make modules_install
```

Check kernel release version:
```
cat include/config/kernel.release
```

Copy new kernel image to boot firmware:
```
sudo cp /home/nc4/linux/arch/arm64/boot/Image /boot/firmware/kernel8.img
```

Reboot into the new kernel:
```
sudo reboot
```

Check the new kernel is loaded
```
uname -r
```
Should see `6.6.67-v8+`

Loaded the DRM MIPI DBI module:
```
sudo modprobe drm_mipi_dbi
```



## Set up the device tree overlay

### Add the following lines to to /boot/firmware/config.txt:
```
sudo nano /boot/firmware/config.txt
```
```
[all]
# ili9488 dirver
dtoverlay=nc4_ili9488
# Use increased debugging level
dtdebug=on
```
Confirm this line is also present in config.txt:
```
dtparam=spi=on
```

### Go to the driver directory:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

### Compile the overlay file to a .dtbo binary:
```
sudo dtc -@ -I dts -O dtb -o /boot/firmware/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
```
More verbose debugging:
```
sudo dtc -@ -f -I dts -O dtb -Wunit_address_vs_reg -Wavoid_unnecessary_addr_size -o /boot/firmware/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
```

### Copy the compiled overlay file to /boot/firmware/overlays/:
```
sudo cp nc4_ili9488.dtbo /boot/firmware/overlays/
```

### Check for the nc4_ili9488.dtbo
```
ls /boot/firmware/overlays/*ili9488*
```

### Print the contents o /boot/firmware/config.txt:
```
cat /boot/firmware/config.txt
```

### Reboot if you are stopping here:
```
sudo reboot
```




## Build the driver

### Go to the driver directory:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

### Do a build clean (Optional)
```
make clean || true
```

### In the driver directory run:
```
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
```
If successful, this produces nc4_ili9488.ko

### Verify the file was created:
```
ls nc4_ili9488.ko
```



## Install the driver

### Create the /lib/modules/$(uname -r)/extra if needed:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
```

### Copy the driver to it:
```
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
```

### Ensure proper permissions for the driver file:
```
sudo chmod u=rw,go=r /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
```

### Verify the driver is available:
```
sudo modinfo /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
```

### Update module dependencies:
```
sudo depmod -a
```



## Load and install the driver:

### Load the driver:
```
sudo modprobe nc4_ili9488
```
If lode fails print kernel logs:
```
dmesg | tail -n 50
```

### Verify the driver is loaded:
```
lsmod | grep nc4_ili9488
```

### Check dmesg for logs:
```
dmesg | grep nc4_ili9488
```
If successful, you should see something like:
- "nc4_ili9488 panel registered at /dev/fb0"
- "nc4_ili9488 panel registered at /dev/fb1"

### To load the driver at every boot, add "nc4_ili9488" to /etc/modules or create a file in /etc/modules-load.d/:
```
echo nc4_ili9488 | sudo tee /etc/modules-load.d/nc4_ili9488.conf
```

### Reboot:
```
sudo reboot
```



## Validate Overlay

### (Optional) Increase the console log level to max (Optional)
```
sudo dmesg -n 8
```
Allows all kernel logs to be displayed for debugging purposes.

### (Optional) Include kernel logging debug glag for more boot info:
```
sudo nano /boot/firmware/cmdline.txt
```
Add to end of file:
```
debug
``` 

### (Never works) Check overlay nodes showing overlay was successfully loaded
```
ls /proc/device-tree/overlays/nc4_ili9488
```
Expected outcome: Directory exists and contains files like `status` and `name`.

### Check if nodes (e.g., panel0 or panel1) exist in the flattened device tree:
```
grep -q "panel0" <(dtc -I fs /proc/device-tree) && echo "Found overlay nodes" || echo "No nodes found"

```

### Check if the kernel logs mention applying the nc4_ili9488 overlay:
```
dmesg | grep -qi "nc4_ili9488" && echo "Overlay logged in kernel logs" || echo "Overlay not logged in kernel logs"
```

### Check active frame buffers
```
ls /dev/fb*
```
If successful, you should see:
- fb0"
- fb1"

### If the overlay does not load and you do not see /dev/fb0 or /dev/fb1 debug overlay loading:
```
dmesg | grep -i 'overlay'
```
Look for lines indicating that the overlay was applied successfully.
```
dmesg | grep dtoverlay
```
```
dmesg | grep firmware
```

### Verify the overlay is referenced in the config.txt:
```
cat /boot/firmware/config.txt | grep dtoverlay
```

### Look for messages like Read config.txt or Read overlay:
```
dmesg | grep -i dt
```




## Validate Driver

### Check if the module is loaded
```
lsmod | grep nc4_ili9488
```
Expected outcome: Shows `nc4_ili9488` in the list with usage count.

### Verify the overlay's boot application if its loaded
```
dmesg | grep -i 'nc4_ili9488'
```
Expected outcome: Should see `Initialized nc4_ili9488` along with any error messages.

### If the module fails to load, try unloading and reloading it
```
sudo rmmod nc4_ili9488
sudo insmod /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
dmesg | grep -i 'nc4_ili9488'
```
Expected outcome: Driver reloads successfully, and logs show initialization messages.

### Check for errors in the .dtbo file
```
sudo dtc -I dtb -O dts -o /dev/null /boot/firmware/overlays/nc4_ili9488.dtbo
```
Expected outcome: Runs without any error messages.



## Uninstall the nc4_ili9488 Driver

### Unload the driver
```
sudo rmmod nc4_ili9488 || sudo modprobe -r nc4_ili9488
```

### Remove the driver file
```
sudo rm /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
```

### Update module dependencies
```
sudo depmod -a
```

### Ensure the device is unbound (if still bound)
```
echo "spi0.0" | sudo tee /sys/bus/spi/drivers/nc4_ili9488/unbind
```

### Remove the overlay file
```
sudo rm /boot/firmware/overlays/nc4_ili9488.dtbo
```

###  Update /boot/firmware/config.txt to remove overlay
```
sudo nano /boot/firmware/config.txt
```
Remove or comment out the following lines:
```
# dtoverlay=nc4_ili9488
# dtdebug=on
```

### Rebuild the initramfs (if required by your system)
```
sudo update-initramfs -u
```

### Confirm the driver is not loaded
```
lsmod | grep nc4_ili9488
```
```
dmesg | grep -i nc4_ili9488
```



## Verify Removal

### Check if the module is still available
```
modinfo nc4_ili9488 || echo "Module nc4_ili9488 not found (expected if removed)."
```

### Check for residual entries in /proc/device-tree
```
grep -ril 'nc4_ili9488' /proc/device-tree/ || echo "No residual device-tree entries for nc4_ili9488."
```

### Verify no kernel logs reference the driver
```
dmesg | grep -i 'nc4_ili9488' || echo "No references to nc4_ili9488 found in dmesg logs."
```

### Check for residual SPI driver bindings for each SPI device
```
if [ -d "/sys/bus/spi/devices/spi0.0" ]; then
    ls -l /sys/bus/spi/devices/spi0.0/driver || echo "No driver bound to spi0.0."
else
    echo "No spi0.0 device found."
fi
```
```
if [ -d "/sys/bus/spi/devices/spi0.1" ]; then
    ls -l /sys/bus/spi/devices/spi0.1/driver || echo "No driver bound to spi0.1."
else
    echo "No spi0.1 device found."
fi
```

### Search for residual configurations in /boot
```
grep -i 'nc4_ili9488' /boot/config.txt || echo "No nc4_ili9488 references in /boot/config.txt."
```
```
grep -ril 'nc4_ili9488' /boot/ || echo "No residual files related to nc4_ili9488 in /boot."
```

### Confirm no residual modules in /lib/modules
```
find /lib/modules/$(uname -r)/ -name '*nc4_ili9488*' || echo "No nc4_ili9488 modules found in /lib/modules."
```



## Debugging: System checks

### Check driver kernel log:
```
dmesg | grep nc4_ili9488
```
Check that:
- SPI wiring and GPIO assignments match your hardware.
- Your image matches the resolution. fbi will scale or crop as needed.

### Check Kernel Logs for Overlay Errors
```
dmesg | grep -i 'overlay'
```

### Check if overlay was successfully loaded:
```
ls /proc/device-tree/overlays/nc4_ili9488
```

### Check if module is loaded:
```
lsmod | grep nc4_ili9488
```

### Verify the overlay's boot application using:
```
dmesg | grep -i 'nc4_ili9488'
```

### Check active frame buffers
```
ls /dev/fb*
```

### Check for SPI 
```
ls /dev/spi*
```

### Directly Inspect the Alias Mapping: Run:
```
cat /sys/firmware/devicetree/base/aliases/gpio
```



## Debugging: Manual Commands

### Manually load the module at runtime:
```
sudo modprobe nc4_ili9488
```

### Manually unload the module at runtime:
```
sudo rmmod nc4_ili9488
```

### Manually load the overlay at runtime:
```
sudo dtoverlay nc4_ili9488
```
```
dmesg | tail -50
```

### Turn the backlight on (maximum brightness):
```
echo 1 | sudo tee /sys/class/backlight/soc:backlight/brightness
```

### Turn the backlight off:
```
echo 0 | sudo tee /sys/class/backlight/soc:backlight/brightness
```

### Draw an image to the fb0 buffer:
```
sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/C01.png
```



## Debugging: General

### Search for a specific file that matches a string:
```
sudo find / -type f -name "*nc4_ili9488*" 2>/dev/null
```

### Search all files that contain a given string
```
sudo grep -rli "nc4_ili9488" / 2>/dev/null
```
```
sudo find / -type f -name "*nc4_ili9488.dtbo*" -exec dirname {} \; | sort -u
```

### Search within subfolders for files that contain a given string
```
sudo grep -rli "nc4_ili9488" /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/ 2>/dev/null
```

### Search for folders with a given string
```
sudo find / -type d -name "*overlays*"
```



## Debugging: Other

Decompile the .dtbo to a .dts
```
sudo dtc -I dtb -O dts -o /home/nc4/TouchscreenApparatus/debug/nc4_ili9488.dts /boot/firmware/overlays/nc4_ili9488.dtbo
```