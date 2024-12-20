# Instructions to build, install, and test the nc4_ili9488 driver.

## Install dependencies

- Make sure you have installed kernel headers and build tools:
```
sudo apt-get update
```
```
sudo apt-get install raspberrypi-kernel-headers build-essential git device-tree-compiler fbi -y
```
The "fbi" tool is used for testing by showing images on the framebuffer.

## Set up the device tree overlay

Add the following lines to to /boot/firmware/config.txt:
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

Go to the driver directory:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

Compile the overlay file to a .dtbo binary:
```
sudo dtc -@ -I dts -O dtb -o /boot/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
```

Print the contents o /boot/firmware/config.txt:
```
cat /boot/firmware/config.txt
```

Reboot if you are stopping here:
```
sudo reboot
```

All commands:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
sudo dtc -@ -I dts -O dtb -o /boot/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts
cat /boot/firmware/config.txt
sudo reboot
```

## Build the driver

Go to the driver directory:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

In the driver directory run:
```
make
```
If successful, this produces nc4_ili9488.ko

Verify the file was created:
```
ls nc4_ili9488.ko
```

All commands:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
make
ls nc4_ili9488.ko
```

## Install the driver

Create the /lib/modules/$(uname -r)/extra if needed:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
```

Copy the driver to it:
```
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
```

Update module dependencies:
```
sudo depmod -a
```

Confirm that the driver is available:
```
modinfo nc4_ili9488
```

All commands:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a
modinfo nc4_ili9488
```

## Load and install the driver:

Load the module:
```
sudo modprobe nc4_ili9488
```

Check dmesg for logs:
```
dmesg | grep nc4_ili9488
```
If successful, you should see something like:
- "nc4_ili9488 panel registered at /dev/fb0"
- "nc4_ili9488 panel registered at /dev/fb1"

To load the driver at every boot, add "nc4_ili9488" to /etc/modules or create a file in /etc/modules-load.d/:
```
echo nc4_ili9488 | sudo tee /etc/modules-load.d/nc4_ili9488.conf
```

## Testing the driver

After loading the driver, you should have /dev/fb0 and /dev/fb1 for each panel.

Turn the backlight on (it should be on by default after initialization):
It should happen automatically due to fb_blank call in the driver.

Test with an image:
```
sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/C01.png
```
You should see the image on the first panel.

For the second panel:
sudo fbi -d /dev/fb1 -T 1 /home/nc4/TouchscreenApparatus/data/images/C01.png

The "-T 1" tells fbi to use the first virtual console.

## Debugging

If the display is blank or distorted, check the kernel log:
```
dmesg | grep nc4_ili9488
```
Check that:
- SPI wiring and GPIO assignments match your hardware.
- Your image matches the resolution. fbi will scale or crop as needed.

## Adding a third panel:
 - To add a third panel later, edit nc4_ili9488-overlay.dts and add another node:
panel2@2 {
compatible = "nc4,ili9488";
reg = <2>;
dc-gpios = <&gpio YOUR_DC_GPIO 0>;
reset-gpios = <&gpio YOUR_RESET_GPIO 0>;
backlight-gpios = <&gpio 18 0>;
spi-max-frequency = <4000000>;
};
 - Re-compile the DT overlay and reboot. The driver will auto-register the new panel as /dev/fb2.
