<% README: nc4_ili9488 DRM/KMS Driver for ILI9488 TFT Panels on Raspberry Pi

## Overview

This document explains how to build, install, and configure the `nc4_ili9488` DRM/KMS driver on a Raspberry Pi running a recent Debian-based distribution with a 6.6.x kernel. It provides instructions for setting up multiple ILI9488 panels connected via SPI, configuring the device tree, and testing the driver.

## Prerequisites

1. Raspberry Pi OS / Debian Bookworm with a kernel supporting DRM and SPI (e.g., `6.6.62+rpt-rpi-v8`).
2. A working kernel source tree or headers for your current kernel (to build the driver).
3. The `nc4_ili9488.c` and `nc4_ili9488.h` driver source files, along with the provided `Makefile` and `Kbuild` file and Device Tree overlay `nc4_ili9488-overlay.dts`.

## Preparing the Environment

- Ensure SPI is enabled in `/boot/firmware/config.txt`:
```
dtparam=spi=on
```

- You will need kernel headers:
```
sudo apt-get update
```
```
sudo apt-get install -y raspberrypi-kernel-headers build-essential git libdrm-dev -y
```

## Building the Driver

- Build the module:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```
```
make
```

- Verify the file was created:
```
ls nc4_ili9488.ko
```

## Installing the Driver

- Copy the kernel module to the appropriate directory:
```
sudo cp /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
```

- Update module dependencies to include the new driver:
```
sudo modprobe nc4_ili9488
```

- Check `dmesg` for output:
```
dmesg | grep nc4_ili9488
```
You should see messages about panels being detected.

## Setting Up the Device Tree Overlay

- Compile the overlay:
```
dtc -@ -I dts -O dtb -o nc4_ili9488-overlay.dtbo nc4_ili9488-overlay.dts
```

- Compile the overlay file to a .dtbo binary in /boot/firmware/overlays/:
```
sudo dtc -@ -I dts -O dtb -o /boot/firmware/overlays/nc4_ili9488.dtbo /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/nc4_ili9488.dts
```

- In `/boot/firmware/config.txt`, add:
```
dtoverlay=nc4_ili9488-overlay
```

- Reboot the system:
```
sudo reboot
```
After reboot, the driver should probe and initialize the panels.

## Testing the Driver

- Check if the DRM device is present:
```
ls /dev/dri/*
```
You should see `/dev/dri/card0` and possibly `/dev/dri/card0-[connector or plane]` entries.

- Install `modetest` (part of libdrm-tests):
```
sudo apt-get install -y libdrm-tests
```

- Run `modetest` to see available connectors and modes:
```
modetest -D /dev/dri/card0
```
You should see connectors for each ILI9488 panel and a 320x480 mode.

- To display a test pattern:
```
modetest -D /dev/dri/card0 -s <connector_id>:320x480-60@XR24
```
Where `<connector_id>` is one of the connectors listed by `modetest`.

## Debugging

- If something goes wrong, check:
```
dmesg | grep nc4_ili9488
```

- Look for initialization messages, SPI communication errors, or panel not found warnings.

- Ensure correct wiring and SPI configuration.

- Confirm that all GPIO pins in the device tree match your wiring.

## Adding More Panels

- To add a third panel:
- Edit the `nc4_ili9488-overlay.dts` to include another `ili9488-panel@2` (with corresponding CE, DC, and RESET pins).
- Recompile and reapply the overlay.
- The driver will detect it on the next boot, and you’ll have another connector in `modetest`.

## Unloading the Driver

- To unload the driver:
```
sudo rmmod nc4_ili9488
```
- If you want it to load automatically on boot, add `nc4_ili9488` to `/etc/modules`.