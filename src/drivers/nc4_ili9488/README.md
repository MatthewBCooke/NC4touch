# Install dependencies

## Main

```
sudo apt-get update
```
```
sudo apt-get install build-essential git fbi bc bison flex libssl-dev -y
```
The "fbi" tool is used for testing by showing images on the framebuffer.
```
sudo apt-get install device-tree-compiler -y
```
```
sudo apt-get install raspberrypi-kernel-headers -y
```
```
sudo apt-get install libdrm-dev
```

Optional:
```
sudo apt install libdrm-tests kmscube
```
```
sudo apt-get install drm-info
```

# KMS

Needed for the driver to work for... reasons?
```
sudo apt-get install kms++
```

But installs a bunch of other shit that needs to be removed:
```
sudo apt-get purge nvidia* openafs-client
```

Manually force remove the problematic modules:
```
sudo dpkg --remove --force-all apfs-dkms jool-dkms openafs-modules-dkms dahdi-dkms xtrx-dkms tp-smapi-dkms rapiddisk-dkms vpoll-dkms gost-crypto-dkms evdi-dkms broadcom-sta-dkms lttng-modules-dkms iptables-netflow-dkms falcosecurity-scap-dkms ddcci-dkms digimend-dkms bbswitch-dkms r8168-dkms
```

Purge Remaining Files:
```
sudo apt-get autoremove --purge
```

Reconfigure the System: 
```
sudo dpkg --configure -a
```

# Setting up the nc4_ili9488 driver

## Update the Pi and reboot

```
sudo apt update && sudo apt upgrade -y
sudo reboot
```

## Install dependencies
   
```
sudo apt install git bc bison flex libssl-dev libncurses5-dev -y
sudo apt-get install raspberrypi-kernel-headers -y
```

Confirm the Raspberry Pi kernel headers were installed correctly by checking if the /build directory exists (Optional):
```
ls /lib/modules/$(uname -r)/build
```

## Set up the device tree overlay
   
Navigate to the directory containing the nc4_ili9488.dts file:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

Compile the overlay file to a .dtbo binary:
```
sudo dtc -@ -I dts -O dtb -o /boot/firmware/overlays/nc4_ili9488.dtbo nc4_ili9488.dts
```

Edit the config.txt file to include the overlay and set SPI parameters:
```
sudo nano /boot/firmware/config.txt
```

Add the following lines to the end:
```
# nc4_ili9488 overlay and SPI parameters
dtoverlay=nc4_ili9488

# Use increased debugging level
dtdebug=on
```

Print the contents o /boot/firmware/config.txt:
```
cat /boot/firmware/config.txt
```

## Build the driver
  
```
cd /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488
```

Do a clean build
```
make clean || true
```

Clean Build Artifacts
```
git clean -fd
```

Build
```
make
```

Verify the file was created:
```
ls nc4_ili9488.ko
```

## Compile the driver

Copy the .ko file to the system module directory:
```
sudo mkdir -p /lib/modules/$(uname -r)/extra
```
```
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
```

Update module dependencies to include the new driver:
```
sudo depmod -a
```
Confirm that the driver is available:
```
modinfo nc4_ili9488
```

Power off:
```
sudo poweroff
```

Unplig and replug the power

## Run checks
    
Increase the console log level (Optional):
```
sudo dmesg -n 8
```

Verify the overlay's boot application using:
```
dmesg | grep -i 'nc4_ili9488'
```
Expected outcomes: Should see `Initialized nc4_ili9488` along with any error messages
If this fails try unloading and reloading the module
```
sudo rmmod nc4_ili9488
sudo insmod /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/nc4_ili9488.ko
dmesg | grep -i 'nc4_ili9488'
```

Run the following command to ensure the nc4_ili9488 overlay was successfully loaded:
```
ls /proc/device-tree/overlays/nc4_ili9488
```
Expected outcomes: the directory exists and contains files like `status` and `name.

Check for errors in the .dtbo
```
sudo dtc -I dtb -O dts -o /dev/null /boot/firmware/overlays/nc4_ili9488.dtbo
```

# Uninstall the nc4_ili9488 driver

## Unload the driver
```
sudo rmmod nc4_ili9488
```
If you encounter "module is in use", run:
```
sudo modprobe -r nc4_ili9488
```

## Remove the Driver File
```
sudo rm /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/nc4_ili9488.ko
```

## Update Module Dependencies
```
sudo depmod
sudo depmod -a
```

## Clear any cached kernel module information
```
sudo modprobe -c | grep nc4_ili9488
```
``` 
"spi0.0" | sudo tee /sys/bus/spi/drivers/nc4_ili9488/unbind
```

## Rebuild the Initramfs (Critical!):
```
sudo update-initramfs -u
```

## Remove the overlay
```
sudo rm /boot/firmware/overlays/nc4_ili9488.dtbo
```

## Comment out lines in config.txt:
```
sudo nano /boot/firmware/config.txt
```
```
# nc4_ili9488 overlay and SPI parameters
dtoverlay=nc4_ili9488
```

## Check Kernel Modules in Use
```
lsmod | grep nc4_ili9488
```

## Power off
Reboot
```
sudo poweroff
```

Unplig and replug the power

## Verify Removal
```
modinfo nc4_ili9488
```

Check for Residual Entries in /proc/device-tree:
```
grep -ril 'nc4_ili9488' /proc/device-tree/
```

Verify No Kernel Logs Reference:
```
dmesg | grep -i 'nc4_ili9488'
```
Expected outcome: No references to nc4_ili9488 in the logs.

Check for Residual SPI Driver Bindings for each SPI device:
```
ls -l /sys/bus/spi/devices/spi0.0/driver
ls -l /sys/bus/spi/devices/spi0.1/driver
```

Search for Residual Configurations
```
grep -i 'nc4_ili9488' /boot/config.txt
```
```
grep -ril 'nc4_ili9488' /boot/
```

Confirm No Residual Modules in /lib/modules
```
find /lib/modules/$(uname -r)/ -name '*nc4_ili9488*'
```

# Debugging the nc4_ili9488 driver

## Check Kernel Logs for Overlay Errors
```
dmesg | grep -i 'overlay'
```

## Verify the overlay's boot application using:
```
dmesg | grep -i 'nc4_ili9488'
```

## Directly Inspect the Alias Mapping: Run:
```
cat /sys/firmware/devicetree/base/aliases/gpio
```

## Check active frame buffers
```
ls /dev/fb*
```

## Manually load/apply the overlay at runtime to get immediate feedback:
```
sudo dtoverlay nc4_ili9488
dmesg | tail -50
```

## Decompile the .dtbo to a .dts
```
sudo dtc -I dtb -O dts -o /home/nc4/TouchscreenApparatus/debug/nc4_ili9488.dts /boot/firmware/overlays/nc4_ili9488.dtbo
```

## Turn the backlight on (maximum brightness):
```
echo 1 | sudo tee /sys/class/backlight/soc:backlight/brightness
```
## Turn the backlight off:
```
echo 0 | sudo tee /sys/class/backlight/soc:backlight/brightness
```

## Draw an image to the fb0 buffer:
```
sudo fbi -d /dev/fb0 -T 1 /home/nc4/TouchscreenApparatus/data/images/A01.bmp
```

## Check for SPI 
```
ls /dev/spi*
```

## Search for a specific file that matches a string:
```
sudo find / -type f -name "*nc4_ili9488*" 2>/dev/null
```

## Search all files that contain a given string
```
sudo grep -rli "nc4_ili9488" / 2>/dev/null
```

## Search within subfolders for files that contain a given string
```
sudo grep -rli "nc4_ili9488" /home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/ 2>/dev/null
```



# Pin Mapping  

## SPI0 Pin Mapping

| **Signal** | **GPIO Pin** | **Physical Pin** |
|------------|--------------|------------------|
| MOSI       | GPIO 10      | Pin 19           |
| MISO       | GPIO 9       | Pin 21           |
| SCLK       | GPIO 11      | Pin 23           |
| CE0        | GPIO 8       | Pin 24           |
| CE1        | GPIO 7       | Pin 26           |

## SPI1 Pin Mapping

| **Signal** | **GPIO Pin** | **Physical Pin** |
|------------|--------------|------------------|
| MOSI       | GPIO 20      | Pin 38           |
| MISO       | GPIO 19      | Pin 35           |
| SCLK       | GPIO 21      | Pin 40           |
| CE0        | GPIO 18      | Pin 12           |
| CE1        | GPIO 17      | Pin 11           |
| CE2        | GPIO 16      | Pin 36           |

## New Mapping

### SPI1
| **LCD**      | **LCD Pin**     | **Pi Header Pin** | **Pi BCM GPIO** | **Pi Label**          | **Description**                 |
|--------------|-----------------|-------------------|-----------------|-----------------------|---------------------------------|
| **ALL**      | VCC             | Pin 1 or Pin 17   | N/A             | 3V3                   | Shared Power supply for all LCDs |
|              | GND             | Pin 6 or Pin 9    | N/A             | GND                   | Shared Ground                   |
|              | MOSI            | Pin 38           | GPIO 20         | MOSI                  | Shared SPI1 data                 |
|              | SCLK            | Pin 40           | GPIO 21         | SCLK                  | Shared SPI1 clock                |
|              | Backlight       | Pin 15           | GPIO 22         |                       | Shared Backlight control        |
| **LCD_0**    | CS              | Pin 12           | GPIO 18         | CE0                   | LCD_0 SPI1 Chip Select           |
|              | DC              | Pin 22           | GPIO 25         |                       | LCD_0 Data/Command signal       |
|              | RES             | Pin 18           | GPIO 24         |                       | LCD_0 Reset signal              |
| **LCD_1**    | CS              | Pin 11           | GPIO 17         | CE1                   | LCD_1 SPI1 Chip Select           |
|              | DC              | Pin 13           | GPIO 27         |                       | LCD_1 Data/Command signal       |
|              | RES             | Pin 16           | GPIO 23         |                       | LCD_1 Reset signal              |
| **LCD_2**    | CS              | Pin 36           | GPIO 16         | CE2                   | LCD_2 SPI1 Chip Select           |
|              | DC              | Pin 29           | GPIO 5          |                       | LCD_2 Data/Command signal       |
|              | RES             | Pin 31           | GPIO 6          |                       | LCD_2 Reset signal              |


## Old Mapping

### SPI0
| **LCD**      | **LCD Pin**     | **Pi Header Pin** | **Pi BCM GPIO** | **Pi Label**          | **Description**                 |
|--------------|-----------------|-------------------|-----------------|-----------------------|---------------------------------|
| **ALL**      | VCC             | Pin 1 or Pin 17   | N/A             | 3V3                   | Shared Power supply for all LCDs |
|              | GND             | Pin 6 or Pin 9    | N/A             | GND                   | Shared Ground                   |
|              | MOSI            | Pin 19           | GPIO 10         | MOSI                  | Shared SPI0 data                 |
|              | SCLK            | Pin 23           | GPIO 11         | SCLK                  | Shared SPI0 clock                |
|              | Backlight       | Pin 12           | GPIO 18         |                       | Shared Backlight control        |
| **LCD_0**    | CS              | Pin 24           | GPIO 8          | CE0                   | LCD_0 SPI0 Chip Select           |
|              | DC              | Pin 22           | GPIO 25         |                       | LCD_0 Data/Command signal       |
|              | RES             | Pin 18           | GPIO 24         |                       | LCD_0 Reset signal              |
| **LCD_1**    | CS              | Pin 26           | GPIO 7          | CE1                   | LCD_1 SPI0 Chip Select           |
|              | DC              | Pin 13           | GPIO 27         |                       | LCD_1 Data/Command signal       |
| **LCD_2**    | CS              | Pin 7            | GPIO 4          |                       | LCD_2 SPI0 Chip Select           |
|              | DC              | Pin 29           | GPIO 5          |                       | LCD_2 Data/Command signal       |
|              | RES             | Pin 31           | GPIO 6          |                       | LCD_2 Reset signal              |

### I2C
| **LCD**      | **LCD Pin**     | **Pi Header Pin** | **Pi BCM GPIO** | **Pi Label** | **Description**      |
|--------------|-----------------|-------------------|-----------------|--------------|----------------------|
| **LCD_0**    | SDA             | undecided         | undecided       | SDA          | LCD_0 I2C data for touch |
|              | SCL             | undecided         | undecided       | SCL          | LCD_0 I2C clock for touch |
| **LCD_1**    | SDA             | undecided         | undecided       | SDA          | LCD_1 I2C data for touch |
|              | SCL             | undecided         | undecided       | SCL          | LCD_1 I2C clock for touch |
| **LCD_2**    | SDA             | undecided         | undecided       | SDA          | LCD_2 I2C data for touch |
|              | SCL             | undecided         | undecided       | SCL          | LCD_2 I2C clock for touch |
