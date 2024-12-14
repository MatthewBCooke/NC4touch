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

3. Save the file and close the editor.

### 3: Configure Wi-Fi for Internet Access

1. Create or edit the `wpa_supplicant.conf` file in the **boot** partition.

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
 
8. Open the repo in VS Code:
   ```
   code .
   ```

9. Close the VS Code instance when you are done.  

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

1. Update the Pi and reboot
   
   ```
   sudo apt update && sudo apt upgrade -y
   sudo reboot
   ```

2. Install dependencies
   
   ```
   sudo apt install git bc bison flex libssl-dev libncurses5-dev -y
   sudo apt-get install raspberrypi-kernel-headers -y
   ```
   
   Confirm the Raspberry Pi kernel headers were installed correctly by checking if the /build directory exists (Optional):
   ```
   ls /lib/modules/$(uname -r)/build
   ```

3. Build the driver
  
   ```
   cd /home/nc4/TouchscreenApparatus/src/lcd/ili9488
   make
   ```
   
   Verify the file was created:
   ```
   ls ili9488.ko
   ```

4. Compile the driver
   
   Copy the kernel module to the appropriate directory:
   ```
   sudo cp ili9488.ko /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/tiny/
   ```
   Update module dependencies to include the new driver:
   ```
   sudo depmod
   ```
   Confirm that the driver is available:
   ```
   modinfo ili9488
   ```

5. Set up the device tree overlay
   
   Navigate to the directory containing the ili-9488.dts file:
   ```
   cd /home/nc4/TouchscreenApparatus/src/lcd/ili9488/rpi-overlays
   ```
   
   Compile the overlay file to a .dtbo binary:
   ```
   sudo dtc -@ -I dts -O dtb -o /boot/overlays/ili-9488.dtbo ili-9488.dts
   ```
   
   Edit the config.txt file to include the overlay and set SPI parameters:
   ```
   sudo nano /boot/firmware/config.txt
   ```
  
   Add the following lines to the end:
   ```
   # ili9488 overlay and SPI parameters
   dtoverlay=ili-9488-overlay
   dtparam=speed=62000000
   dtparam=rotation=90
   ```
   
   Reboot:
   ```
   sudo reboot
   ```
   
   Run the following command to ensure the ili-9488 was successfully loaded:
   ```
   ls /proc/device-tree/overlays/ili-9488
   ```
   Expected outcomes: the directory exists and contains files like `status` and `name.
   
   Check for errors in the .dtbo
   ```
   sudo dtc -I dtb -O dts -o /dev/null /boot/overlays/ili-9488.dtbo
   ```

6. Temporarily reinable HDMI to use a monitor 
   
   You cannot use a monitor (HDMI) with the ILI9488 driver installed.
   
   Disable the dtoverlay for the ILI9488:
   ```
   sudo nano /boot/firmware/config.txt
   ```
   
   Comment out the line:
   ```
   #dtoverlay=ili-9488
   ```
  
   Change this back when you need to use the ILI9488 driver.

### BUNCH OF SHIT
Copy the ili9488.ko module to the kernel's module directory:

bash
Copy code
sudo cp ili9488.ko /lib/modules/`uname -r`/kernel/drivers/gpu/drm/tiny/
Update module dependencies:

bash
Copy code
sudo depmod
Attempt to load the module:

bash
Copy code
sudo modprobe ili9488
Verify that the module is loaded:

bash
Copy code
lsmod | grep ili9488

Step 1: Manually Load the Driver
sudo modprobe ili9488

Verify the Driver is Loaded, run the following command:
lsmod | grep ili9488

Confirm the framebuffer device is registered correctly.
ls /dev | grep fb

Verify the framebuffer device name.
cat /sys/class/graphics/fb0/name

Test the framebuffer by displaying an image.
sudo fbi -d /dev/fb0 -T 1 /path/to/test_image.bmp

Set pin high
gpioset gpiochip0 23=1

Remove the .git Folder: This folder makes the directory a separate Git repository.
rm -rf .git

Add the lcd/ili9488 Folder to the Main Repository:
git add lcd/ili9488


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

# Setting up C++

Run setup.sh:
   ```
   sudo ./setup.sh
   ```

# Pin Mapping

## Pi to LCD
| **LCD Pin**     | **Raspberry Pi GPIO Pin**                    | **Description**            
|-----------------|----------------------------------------------|----------------------------
| **VCC**         | Pin 1 or Pin 17 (3.3V)                       | Shared Power supply for the LCD   
| **GND**         | Pin 6 or Pin 9 (GND)                         | Shared Ground                     
| **DC**          | Pin 22 (GPIO 25)                             | Shared Data/Command signal        
| **RES**         | Pin 18 (GPIO 23)                             | Shared Reset signal               
| **Backlight**   | Pin 15 (GPIO 22)                             | Shared Backlight control          
| **MOSI**        | Pin 19 (GPIO 10, MOSI)                       | Shared SPI data from Pi to LCD    
| **SCLK**        | Pin 23 (GPIO 11, SCLK)                       | Shared SPI clock                  
| **CS**          | Pin 24 (GPIO 8, CE0)                         | LCD_0 SPI chip select             
| **INT**         | Pin 11 (GPIO 17, SCLK)                       | LCD_0 Touch interrupt              
| **SDA**         | Pin 3 (GPIO 2, SDA)                          | LCD_0 I2C data for touch control  
| **SCL**         | Pin 5 (GPIO 3, SCL)                          | LCD_0 I2C clock for touch control 
| **SDA**         | Pin 3 (GPIO 4, SDA)                          | LCD_1 I2C data for touch control  
| **SCL**         | Pin 5 (GPIO 5, SCL)                          | LCD_1 I2C clock for touch control 
| **SDA**         | Pin 3 (GPIO 8, SDA)                          | LCD_2 I2C data for touch control  
| **SCL**         | Pin 5 (GPIO 9, SCL)                          | LCD_2 I2C clock for touch control   