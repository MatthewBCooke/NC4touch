# README: nc4_ili9488 DRM/KMS Driver for ILI9488 TFT Panels on Raspberry Pi

## Overview
This document provides step-by-step instructions to build, install, and test the nc4_ili9488 driver on a Raspberry Pi running a Linux kernel with DRM support.

## Prerequisites:
- A Raspberry Pi 4 running a Linux kernel with DRM enabled (e.g., Raspberry Pi OS Bookworm)
- SPI enabled in /boot/firmware/config.txt
- Device Tree overlay to define the panels and their connections
- A toolchain to build kernel modules (kernel headers, gcc, make)
- The nc4_ili9488.c driver source code and associated files

## Steps:

### Ensure SPI and DRM are enabled:

In /boot/firmware/config.txt, confirm:
```
dtparam=spi=on
```
If you have a custom overlay for SPI and your panels, ensure it is referenced here.

### Set up the device tree overlay

Compile the overlay file to a .dtbo binary:
```
sudo dtc -@ -I dts -O dtb -o /boot/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
```

Add to /boot/firmware/config.txt:
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

Print the contents o /boot/firmware/config.txt:
```
cat /boot/firmware/config.txt
```

### Install necessary kernel headers:
```
sudo apt-get update
```
```
sudo apt-get install -y raspberrypi-kernel-headers build-essential
```

### Build the nc4_ili9488 driver:
Run:
```
make -C /lib/modules/`uname -r`/build M=`pwd` modules
```
This should produce nc4_ili9488.ko

- Verify the file was created:
```
ls nc4_ili9488.ko
```

### Install the driver:

Install the module into the preferred location:
```
sudo cp nc4_ili9488.ko /lib/modules/`uname -r`/kernel/drivers/gpu/drm/tiny/
```

Update module dependencies:
```
sudo depmod -a
```

Then load it:
```
sudo modprobe nc4_ili9488
```

Check dmesg for logs:
```
dmesg | grep nc4_ili9488
```

You should see initialization messages.

### Testing the Driver:
After loading the driver and rebooting (if necessary), you should have a /dev/dri/card0 device.
Use DRM/KMS utilities like modetest to see available connectors:
modetest -D 0

You should see connectors for each panel defined in the DT.

To display an image:
- Convert your PNG to XRGB8888 raw format or use DRM APIs directly.
- You can write a small userspace program using libdrm to set a mode and draw the image.
- Alternatively, you can use existing DRM sample programs to display a test pattern.

Since no fbdev emulation is included, tools like fbi will not work directly.
Instead, consider writing a small C or Python program that uses DRM APIs or calling a DRM utility program.

If you need debugging info:
```
dmesg | grep nc4_ili9488
```

This will show you logs from probe, panel init, and any SPI transfer failures.
