
# Setting up the nc4_ili9488 driver

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

## Online resource
```
https://pinout.xyz/pinout/
```
## Pi SPI0 Pin Mapping

| **Signal** | **Physical Pin** | **GPIO Pin** |
|------------|------------------|--------------|
| MOSI       | Pin 19           | GPIO 10      |
| MISO       | Pin 21           | GPIO 9       |
| SCLK       | Pin 23           | GPIO 11      |
| CE0        | Pin 24           | GPIO 8       |
| CE1        | Pin 26           | GPIO 7       |

## Pi SPI1 Pin Mapping

| **Signal** | **Physical Pin** | **GPIO Pin** |
|------------|------------------|--------------|
| MOSI       | Pin 38           | GPIO 20      |
| MISO       | Pin 35           | GPIO 19      |
| SCLK       | Pin 40           | GPIO 21      |
| CE0        | Pin 12           | GPIO 18      |
| CE1        | Pin 11           | GPIO 17      |
| CE2        | Pin 36           | GPIO 16      |

## Pi Hardware I²C Buses

| **Bus** | **Signal** | **Physical Pin(s)** | **GPIO Pin(s)** | **Description**                                                                                   |
|---------|------------|---------------------|-----------------|---------------------------------------------------------------------------------------------------|
| I²C0    | SDA        | Pin 27              | GPIO0           | Primarily used for HAT EEPROM identification; not recommended for general use.                    |
|         | SCL        | Pin 28              | GPIO1           |                                                                                                   |
| I²C1    | SDA        | Pin 3               | GPIO2           | Default I²C bus; includes fixed 1.8 kΩ pull-up resistors to 3.3V.                                 |
|         | SCL        | Pin 5               | GPIO3           |                                                                                                   |
| I²C3    | SDA        | Pin 7               | GPIO4           | Additional hardware I²C bus; can be enabled via Device Tree overlay.                              |
|         | SCL        | Pin 29              | GPIO5           |                                                                                                   |
| I²C4    | SDA        | Pin 31              | GPIO6           | Another hardware I²C bus; configurable through Device Tree overlay.                               |
|         | SCL        | Pin 32              | GPIO7           |                                                                                                   |
| I²C5    | SDA        | Pin 24              | GPIO8           | Shares pins with SPI0; ensure no conflicts when using this bus.                                   |
|         | SCL        | Pin 21              | GPIO9           |                                                                                                   |
| I²C6    | SDA        | Pin 19              | GPIO10          | Shares pins with SPI0; use with caution to avoid conflicts.                                       |
|         | SCL        | Pin 23              | GPIO11          |                                                                                                   |


## Our Mapping

### SPI1
| **LCD**      | **LCD Pin**     | **Pi Header Pin** | **Pi BCM GPIO** | **Pi Label**          | **Description**                 |
|--------------|-----------------|-------------------|-----------------|-----------------------|---------------------------------|
| **ALL**      | VCC             | Pin 1 or Pin 17   | N/A             | 3V3                   | Shared Power supply for all LCDs |
|              | GND             | Pin 6 or Pin 9    | N/A             | GND                   | Shared Ground                   |
|              | MOSI            | Pin 38           | GPIO 20         | MOSI                  | Shared SPI1 data                 |
|              | SCLK            | Pin 40           | GPIO 21         | SCLK                  | Shared SPI1 clock                |
|              | Backlight       | Pin 13           | GPIO 27         |                       | Shared Backlight control        |
| **LCD_0**    | CS              | Pin 12           | GPIO 18         | CE0                   | LCD_0 SPI1 Chip Select           |
|              | RES             | Pin 22           | GPIO 25         |                       | LCD_0 Reset signal              |
|              | DC              | Pin 18           | GPIO 24         |                       | LCD_0 Data/Command signal       |
| **LCD_1**    | CS              | Pin 11           | GPIO 17         | CE1                   | LCD_1 SPI1 Chip Select           |
|              | RES             | Pin 16           | GPIO 23         |                       | LCD_1 Reset signal              |
|              | DC              | Pin 15           | GPIO 22         |                       | LCD_1 Data/Command signal       |
| **LCD_2**    | CS              | Pin 36           | GPIO 16         | CE2                   | LCD_2 SPI1 Chip Select           |
|              | RES             | Pin 33           | GPIO 13         |                       | LCD_2 Reset signal              |
|              | DC              | Pin 32           | GPIO 12         |                       | LCD_2 Data/Command signal       |

### I2C
| **LCD**      | **LCD Pin**     | **Pi Header Pin** | **Pi BCM GPIO** | **Pi Label** | **Description**                    |
|--------------|-----------------|-------------------|-----------------|--------------|------------------------------------|
| **LCD_0**    | SDA             | Pin 3             | GPIO2           | SDA          | LCD_0 I²C data for touch (I²C1)    |
|              | SCL             | Pin 5             | GPIO3           | SCL          | LCD_0 I²C clock for touch (I²C1)   |
| **LCD_1**    | SDA             | Pin 7             | GPIO4           | SDA          | LCD_1 I²C data for touch (I²C3)    |
|              | SCL             | Pin 29            | GPIO5           | SCL          | LCD_1 I²C clock for touch (I²C3)   |
| **LCD_2**    | SDA             | Pin 31            | GPIO6           | SDA          | LCD_2 I²C data for touch (I²C4)    |
|              | SCL             | Pin 32            | GPIO7           | SCL          | LCD_2 I²C clock for touch (I²C4)   |



