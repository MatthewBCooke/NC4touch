# Setting Up Raspberry Pi OS with SSH and VS Code Remote Development

## Install Raspberry Pi OS

1. Instal Raspberry Pi Imager `https://www.raspberrypi.com/software/`.

2. Plug a micro SD card into an addapter on your computer.

3. Set the following:
   - Rasberry Pi Device: `Raspberry Pi 5`
   - Operating System: `Raspberry Pi OS (64-bit)`
   - Operating System: The drive associated with your SD card.

4. Edit settings when prompted:
   - **Set username and password**
      - **Username**: `nc4`
      - **Password**: `1434`
   - **Configure wireless LAN**
      - **SSID**: `NC4_Neurogenesis_Exposure`
      - **Password**: `nc4lab1434`
      - **Wireless LAN Country**: `CA` 
   - **Set lacale settings**
      - Check the box
      - **Timezone**: `US/Vanvouver`
      - **Keyboard**: `us`
- **SERVICES** Tab
   - **Enable SSH**: Checked and set to `Use password authentication` 

5. Apply the setup settings to the SD card.

6. Install Updates

   Plug in the SD card and power on the Pi
   Open a terminal and run:
   ```
   sudo apt update
   sudo apt full-upgrade -y
   ``` 
   
   Reboot:
   ```
   sudo reboot
   ```

## Enable SSH, SPI and GPIO on the Raspberry Pi if needed

1. Boot the Raspberry Pi.

2. Open a terminal on the Pi and run:
   ```
   sudo raspi-config
   ```

3. Enable SSH:
   - **Interface Options > SSH**
   - Select **Enable**.

4. Enable SPI:
   - **Interface Options > SPI**
   - Select **Enable**.

5. Enable I2C:
   - **Interface Options > I2C**
   - Select **Enable**.

6. Reboot
   ```
   sudo reboot
   ```


## Assign a Static IP and Configure Ethernet and Internet Access for the Raspberry Pi

### 1: Power Off and Prepare the SD Card

1. Power off the Raspberry Pi by running:
   ```
   sudo poweroff
   ```

2. Wait for the Pi to shut down, then remove the SD card.

3. Insert the SD card into your computer and open the **boot** partition.

### 2: Configure a Static IP for the Ethernet Interface

1. Open the `cmdline.txt` file in the **boot** partition using a text editor.

2. Add the following to the end of the single line (ensure everything remains on a single line):
   ```
   ip=169.254.55.240::0.0.0.0:255.255.0.0::eth0:off
   ```
- Explanation:
  - `169.254.55.240`: Static IP for the Raspberry Pi’s Ethernet interface.
  - `0.0.0.0`: No default gateway for Ethernet (traffic won’t be routed through this interface).
  - `255.255.0.0`: Subnet mask for the Ethernet interface.
  - `eth0:off`: Specifies the Ethernet interface and disables DHCP.

3. At this stage you can also disable the Pi from loading the desktop by adding this line as well:
   ```
   systemd.unit=multi-user.target autologin-user=nc4 nosplash
   ```


3. Save the file and close the editor.

### 3: Configure Wi-Fi for Internet Access

1. Create or edit the `wpa_supplicant.conf` file in the **boot** partition.
You can do this from your SSH connection using:
```
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

2. Add the following content:
   ```
   country=CA
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1

   network={
       ssid="NC4_Neurogenesis_Exposure"
       psk="nc4lab1434"
   }
   ```
   Or
   ```
   country=CA
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1

   network={
       ssid="poserguru_s24"
       psk="funkstar"
   }
   ```

3. Save the file and eject the SD card.

### 4: Boot the Raspberry Pi

1. Reinsert the SD card into the Raspberry Pi.

2. Connect an Ethernet cable between your computer and the Pi.

3. Power on the Raspberry Pi.

### 5: Connect to the Raspberry Pi via SSH

1. On your computer, open a terminal or SSH client.

2. Ping the Raspberry Pi:
   ```bash
   ping 169.254.55.240
   ```

3. If the ping is successful, SSH into the Raspberry Pi:
   ```bash
   ssh nc4@169.254.55.240
   ```
   If you get a warning about the hot key changing open:
   ```
   C:\Users\lester\.ssh\known_hosts
   ```
   Delete the line:
   ssh-keygen -R 169.254.55.240

4. When prompted:
   - Type `yes` to continue connecting.
   - Enter the password: `1434`.

5. After connecting via SSH, varify the Wi-Fi connection:
   ```
   ping -c 4 google.com
   ```

6. Verify the connection works, then exit the SSH session:
   ```bash
   exit
   ```

## Set Up Remote Development in VS Code

1. Open Visual Studio Code on your Windows PC.

2. Press `Ctrl + Shift + P` to open the Command Palette.

3. Search for and select:
   ```
   Remote-SSH: Add New SSH Host...
   ```

4. Enter the Raspberry Pi's SSH connection string:
   ```
   nc4@169.254.55.240
   ```

5. Save the configuration when prompted (e.g., `~/.ssh/config`).

6. Click **Connect**.

7. A new VS Code window will open.

8. When prompted to select the platform, choose:
   ```
   Linux
   ```

9. Enter the password again: `1434`.

10. VS Code will automatically download and set up the remote server on the Raspberry Pi.


## Set up search by prefix functionality (Optional)
   
   1. Open the ~/.bashrc file for editing:
   ```
   nano ~/.bashrc
   ```
   
   2. Add the following lines to your ~/.bashrc:
   ```
   # Enable history search with up/down arrows
   bind '"\e[A": history-search-backward'
   bind '"\e[B": history-search-forward'
   ```

   3. Save the pashrc and source it:
   ```
   source ~/.bashrc
   ```

## Setup User Permisions for GPIO and SPI (Optional?)

1. Add the User to the gpio and spi Groups
   To ensure the user can access GPIO and SPI without sudo, run:
   ```
   sudo usermod -aG gpio,spi $(whoami)
   ```

2. Reboot the Raspberry Pi:
   ```
   sudo reboot
   ```

3. Check Group Membership
   Verify that the user has been added to the gpio and spi groups:
   ```
   groups
   ```
   Ensure the output includes both gpio and spi.

4. Test GPIO Pin Configuration:
   
   Install libgpiod Tools:
   Install the GPIO tools package to manage GPIO on the Raspberry Pi 5:
   ```
   sudo apt install gpiod -y
   ```
   
   Check GPIO Line Information:
   Use the gpioinfo command to list all GPIO lines and their statuses:
   ```
   gpioinfo
   ```
   If this command executes without errors and lists GPIO details, you have sufficient permissions to access GPIO.

5. Check SPI Setup

   Check if the SPI device files are available:
   ```
   ls /dev/spi*
   ```
   Output should show:
   ```
   /dev/spidev0.0
   /dev/spidev0.1
   ```

   Check the status of the SPI kernel module:
   ```
   lsmod | grep spi
   ```
   The output should include lines like:
   ```
   spi_bcm2835            49152  0
   ```

   Check the permissions of the SPI device files:
   ```
   ls -l /dev/spi*
   ```
   Example output:
   ```
   crw-rw---- 1 root spi 153, 0 Dec 10 10:00 /dev/spidev0.0
   crw-rw---- 1 root spi 153, 1 Dec 10 10:00 /dev/spidev0.1
   ```

## Setup access to GitHub

1. Generate a new SSH key:
   ```
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
   - Replace `your_email@example.com` with your GitHub email.
   ```
   ssh-keygen -t ed25519 -C "adamwardlester@gmail.com"
   ```
   - Press `Enter` to accept all defaults and skip passphrase.

2. Print the public key:
   ```
   cat ~/.ssh/id_ed25519.pub
   ```
   - Copy the generated key.

3. Add the key to GitHub:
   - Go to https://github.com/settings/keys.
   - Click **New SSH key**.
   - **Title**: `nc4-raspi5_x` (e.g., `nc4-raspi5_1`)
   - Paste the copied key and save.

4. Test the connection:
   ```
   ssh -T git@github.com
   ```
   Type `yes` and press `Enter`.

5. Clone the repository:
   ```
   git clone git@github.com:NC4Lab/TouchscreenApparatus.git
   ```

6. Set Your Git Username: Run this command in the VS Code terminal (connected to your Pi):
   ```
   git config --global user.name "Your Name"
   ```
   ```
   git config --global user.name "AdamWardLester"
   ```

7. Set Your Git Email: Run this command in the same terminal:
   ```
   git config --global user.email "your_email@example.com"
   ```
   ```
   git config --global user.email "adamwardlester@gmail.com"
   ```

8. Verify Configuration: 
   ```
   git config --global --list
   ```

# Working is SSH
1. Open Visual Studio Code on your Windows PC.

2. Press `Ctrl + Shift + P` to open the Command Palette.


3. Search for and select:
   ```
   Remote-SSH: Add New SSH Host...
   ```
4. Enter the Raspberry Pi's SSH connection string:
   ```
   nc4@169.254.55.240
   ```

5. Select your config when prompted (e.g., `~/.ssh/config`).

6. Click **Connect**.

7. Go to the repo:
   ```
   cd TouchscreenApparatus
   ```

8. Enter the Pi password `1434` in the VS Code search bar.
 
9. Open the repo in VS Code:
   ```
   code .
   ```

10. Close the VS Code instance when you are done.  

# Enabling additional I2C busses on the Pi

1. Edit the Configuration File: Open the config.txt file:
   ```
   sudo nano /boot/firmware/config.txt
   ```

2. Add the Following Lines to enable additional buses 3 and 4 after `dtparam=i2c_arm=on`:
   ```
   dtoverlay=i2c3              # Enables I²C Bus 3
   dtoverlay=i2c4              # Enables I²C Bus 4
   ```

3. Save and Exit: Save the file (Ctrl+O, Enter, Ctrl+X)

4. Reboot:
   ```
   sudo reboot
   ```

5. Varify the busses by listing them:
   ```
   ls /dev/i2c-*
   ```
   You should see:
   ```
   /dev/i2c-1
   /dev/i2c-3 (or some other number sufix)
   /dev/i2c-4 (or some other number sufix)
   ```
   
# Setting up the ili9488 driver

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

## Build the driver
  
```
cd /home/nc4/TouchscreenApparatus/src/drivers/ili9488
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
ls ili9488.ko
```

## Compile the driver
   
Copy the kernel module to the appropriate directory:
```
sudo cp /home/nc4/TouchscreenApparatus/src/drivers/ili9488/ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
```
Update module dependencies to include the new driver:
```
sudo depmod -a
```
Confirm that the driver is available:
```
modinfo ili9488
```

## Set up the device tree overlay
   
Navigate to the directory containing the ili9488.dts file:
```
cd /home/nc4/TouchscreenApparatus/src/drivers/ili9488/rpi-overlays
```

Compile the overlay file to a .dtbo binary:
```
sudo dtc -@ -I dts -O dtb -o /boot/firmware/overlays/ili9488.dtbo ili9488.dts
```

Edit the config.txt file to include the overlay and set SPI parameters:
```
sudo nano /boot/firmware/config.txt
```

Add the following lines to the end:
```
# ili9488 overlay and SPI parameters
dtoverlay=ili9488
dtparam=speed=62000000
dtparam=rotation=90

# Use increased debugging level
dtdebug=on
```

Print the contents o /boot/firmware/config.txt:
```
cat /boot/firmware/config.txt
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
dmesg | grep -i 'ili9488'
```
Expected outcomes: Should see `Initialized ili9488` along with any error messages
If this fails try unloading and reloading the module
```
sudo rmmod ili9488
sudo insmod /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/ili9488.ko
dmesg | grep -i 'ili9488'
```

Run the following command to ensure the ili9488 overlay was successfully loaded:
```
ls /proc/device-tree/overlays/ili9488
```
Expected outcomes: the directory exists and contains files like `status` and `name.

Check for errors in the .dtbo
```
sudo dtc -I dtb -O dts -o /dev/null /boot/firmware/overlays/ili9488.dtbo
```

# Uninstall the ili9488 driver

## Unload the driver
```
sudo rmmod ili9488
```
If you encounter "module is in use", run:
```
sudo modprobe -r ili9488
```

## Remove the Driver File
```
sudo rm /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/ili9488.ko
```

## Update Module Dependencies
```
sudo depmod
```

## Clear any cached kernel module information
```
sudo modprobe -c | grep ili9488
```
``` 
"spi0.0" | sudo tee /sys/bus/spi/drivers/ili9488/unbind
```

## Rebuild the Initramfs (Critical!):
```
sudo update-initramfs -u
```

## Remove the overlay
```
sudo rm /boot/firmware/overlays/ili9488.dtbo
```

## Comment out lines in config.txt:
```
sudo nano /boot/firmware/config.txt
```
```
# ili9488 overlay and SPI parameters
dtoverlay=ili9488
dtparam=speed=62000000
dtparam=rotation=90
```

## Check Kernel Modules in Use
```
lsmod | grep ili9488
```

## Power off
Reboot
```
sudo poweroff
```

Unplig and replug the power

## Verify Removal
```
modinfo ili9488
```

Check for Residual Entries in /proc/device-tree:
```
grep -ril 'ili9488' /proc/device-tree/
```

Verify No Kernel Logs Reference:
```
dmesg | grep -i 'ili9488'
```
Expected outcome: No references to ili9488 in the logs.

Check for Residual SPI Driver Bindings for each SPI device:
```
ls -l /sys/bus/spi/devices/spi0.0/driver
ls -l /sys/bus/spi/devices/spi0.1/driver
```

Search for Residual Configurations
```
grep -i 'ili9488' /boot/config.txt
```
```
grep -ril 'ili9488' /boot/
```

Confirm No Residual Modules in /lib/modules
```
find /lib/modules/$(uname -r)/ -name '*ili9488*'
```

# Debugging the ili9488 driver

## Check Kernel Logs for Overlay Errors
```
dmesg | grep -i 'overlay'
```

## Verify the overlay's boot application using:
```
dmesg | grep -i 'ili9488'
```

## Directly Inspect the Alias Mapping: Run:
```
cat /sys/firmware/devicetree/base/aliases/gpio
```

## Check active frame buffers
```
ls /dev/fb*
```

## Manually load the overlay at runtime to get immediate feedback:
```
sudo dtoverlay ili9488
dmesg | tail -50
```

## Decompile the .dtbo to a .dts
```
sudo dtc -I dtb -O dts -o /home/nc4/TouchscreenApparatus/debug/ili9488.dts /boot/firmware/overlays/ili9488.dtbo
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
sudo find / -type f -name "*ili9488*" 2>/dev/null
```

## Search all files that contain a given string
```
sudo grep -rli "ili9488" / 2>/dev/null
```

## Search within subfolders for files that contain a given string
```
sudo grep -rli "ili9488" /home/nc4/TouchscreenApparatus/src/drivers/ili9488/ 2>/dev/null
```

# Setting up python environment
1. Update and Upgrade Raspberry Pi Packages:
   ```
   sudo apt update && sudo apt upgrade -y

   ```

2. Install general essentials:
   ```
   sudo apt install build-essential git python3-dev python3-venv python3-pip -y
   ```

3. Project-specific essentials:
   ```
   sudo apt install gpiod libgpiod-dev spi-tools fbset device-tree-compiler -y
   sudo apt install lgpio
   ```

4. Create a Virtual Environment
   - Navigate to the project directory and create an environement
   ```
   cd ~/TouchscreenApparatus
   python3 -m venv venv
   ```

5. Activate the Virtual Environment
   ```
   source venv/bin/activate
   ```

6. Install Project specific Packages:
   ```
   pip install gpiod numpy pillow spidev
   ```

7. Install LCD libraries:
   ```
   pip install luma.lcd luma.core
   ```

8. Keep Dependencies Organized: 
   - Create `requirements.txt` file:
   ```
   pip freeze > requirements.txt
   ```
   Dependencies can be reinstalled using:
   ```
   pip install -r requirements.txt
   ```
   Rerun the 'Create' command when libraries are modified.

# Random

Connect to my hotspot:
```
iwgetid -r
```
```
sudo nmcli dev wifi connect "poserguru_s24" password "funkstar"
```

Varify:
```
nmcli connection show --active
```

Git BS:
```
cd /home/nc4
sudo cp -r ~/TouchscreenApparatus ~/TouchscreenApparatus_backup
diff -r --exclude='.lgd-nfy0' /home/nc4/TouchscreenApparatus /home/nc4/TouchscreenApparatus_backup
cd /home/nc4/TouchscreenApparatus
git fsck --full | grep -o 'git/objects/[0-9a-f]*/[0-9a-f]*' | xargs rm -f
find .git/objects -type f -empty -delete
git stash
git fetch --all
git reset --hard origin/main
git stash pop
git add .
Commit changes
```


# Pin Mapping  


| **LCD**      | **LCD Pin**     | **Raspberry Pi GPIO Pin**    | **Description**                |
|--------------|-----------------|-----------------------------|--------------------------------|
| **ALL**      | VCC             | Pin 1 or Pin 17 (3.3V)       | Shared Power supply for all LCDs |
|              | GND             | Pin 6 or Pin 9 (GND)         | Shared Ground                   |
|              | MOSI            | Pin 19 (GPIO 10, MOSI)       | Shared SPI data                 |
|              | SCLK            | Pin 23 (GPIO 11, SCLK)       | Shared SPI clock                |
|              | Backlight       | Pin 12 (GPIO 18)             | Shared Backlight control        |
| **LCD_0**    | CS              | Pin 24 (GPIO 8, CE0)         | LCD_0 SPI Chip Select           |
|              | DC              | Pin 22 (GPIO 25)             | LCD_0 Data/Command signal       |
|              | RES             | Pin 18 (GPIO 24)             | LCD_0 Reset signal              |
|              | SDA             | Pin 3 (GPIO 2, SDA)          | LCD_0 I2C data for touch        |
|              | SCL             | Pin 5 (GPIO 3, SCL)          | LCD_0 I2C clock for touch       |
| **LCD_1**    | CS              | Pin 26 (GPIO 7, CE1)         | LCD_1 SPI Chip Select           |
|              | DC              | Pin 13 (GPIO 27)             | LCD_1 Data/Command signal       |
|              | RES             | Pin 16 (GPIO 23)             | LCD_1 Reset signal              |
|              | SDA             | Pin 3 (GPIO 2, SDA)          | LCD_1 I2C data for touch        |
|              | SCL             | Pin 5 (GPIO 3, SCL)          | LCD_1 I2C clock for touch       |
| **LCD_2**    | CS              | Pin 7 (GPIO 4)               | LCD_2 SPI Chip Select           |
|              | DC              | Pin 29 (GPIO 5)              | LCD_2 Data/Command signal       |
|              | RES             | Pin 31 (GPIO 6)              | LCD_2 Reset signal              |
|              | SDA             | Pin 3 (GPIO 2, SDA)          | LCD_2 I2C data for touch        |
|              | SCL             | Pin 5 (GPIO 3, SCL)          | LCD_2 I2C clock for touch       |


