# Raspberry Pi Project Setup: Required Packages and Verification

This document outlines the required packages for your Raspberry Pi project, organized into logical groups. Each section includes installation commands, confirmation steps, and optional cleanup.

---

## **1. Core Development Tools**
### **Install**:
```bash
sudo apt-get install build-essential git bc bison flex libssl-dev -y
```

### **Purpose**:
- **`build-essential`**: Provides GCC, `make`, and other essential build tools.
- **`git`**: Source code management and cloning repositories.
- **`bc`, `bison`, `flex`**: Often required for building kernels and modules.
- **`libssl-dev`**: Provides SSL development libraries.

### **Confirm**:
1. **Check Tools**:
   ```bash
   gcc --version     # Confirms GCC is installed
   make --version    # Confirms `make` is installed
   git --version     # Confirms `git` is installed
   ```
2. **Check Libraries**:
   Look for `libssl-dev`:
   ```bash
   dpkg -l | grep libssl-dev
   ```

---

## **2. Kernel Headers and Device Tree**
### **Install**:
```bash
sudo apt-get install raspberrypi-kernel-headers device-tree-compiler -y
```

### **Purpose**:
- **`raspberrypi-kernel-headers`**: Required for building kernel modules.
- **`device-tree-compiler`**: Compiles `.dts` files into `.dtbo` overlays for display configuration.

### **Confirm**:
1. **Check Kernel Headers**:
   ```bash
   ls /lib/modules/$(uname -r)/build
   ```
   - If this directory exists, the kernel headers are installed correctly.
2. **Check Device Tree Compiler**:
   ```bash
   dtc --version
   ```
   - Confirms `dtc` is installed.

---

## **3. DRM Development and Testing**
### **Install**:
```bash
sudo apt-get install libdrm-dev libdrm-tests kmscube drm-info -y
```

### **Purpose**:
- **`libdrm-dev`**: Development libraries for interacting with the Direct Rendering Manager (DRM).
- **`libdrm-tests`**: Tools for debugging DRM resources.
- **`kmscube`**: Tests KMS (Kernel Mode Setting) functionality.
- **`drm-info`**: Provides detailed DRM resource information.

### **Confirm**:
1. **Check Development Libraries**:
   ```bash
   dpkg -l | grep libdrm-dev
   ```
2. **Test DRM Tools**:
   - Run `kmscube`:
     ```bash
     kmscube
     ```
     - Tests KMS and DRM pipeline functionality.
   - Check DRM info:
     ```bash
     drm-info
     ```

---

## **4. Framebuffer Tools**
### **Install**:
```bash
sudo apt-get install fbi -y
```

### **Purpose**:
- **`fbi`**: A framebuffer image viewer for testing display configurations.

### **Confirm**:
1. **Test Framebuffer Devices**:
   - Display an image on the framebuffer:
     ```bash
     sudo fbi -d /dev/fb0 -T 1 /path/to/test-image.jpg
     ```
     - Replace `/path/to/test-image.jpg` with an actual image file.

---

## **5. Optional Tools**

### **Install Micro Text Editor**:
```bash
sudo apt install micro -y
```

### **Purpose**:
- **`micro`**: A lightweight and user-friendly text editor, useful for editing configuration files like `config.txt` or `.json` settings.

### **Confirm**:
- Open the editor:
  ```bash
  micro --version
  ```
- Configure settings (optional):
  ```bash
  micro ~/.config/micro/settings.json
  ```

### **Install Python for Scripting**:
```bash
sudo apt-get install python3 python3-pip -y
```

### **Purpose**:
- **`python3`**: Provides Python 3 for scripting and development tasks.
- **`python3-pip`**: Allows installing Python packages via `pip`.

### **Confirm**:
1. **Check Python Version**:
   ```bash
   python3 --version
   ```
2. **Test Pip**:
   ```bash
   pip3 --version
   ```

### **Install DKMS**:
```bash
sudo apt-get install dkms -y
```

### **Purpose**:
- **`dkms`**: Automates building and installing kernel modules, useful for maintaining module compatibility during kernel upgrades.

### **Confirm**:
- Check DKMS status:
  ```bash
  dkms status
  ```

### **Install Logging and Monitoring Tools**:
```bash
sudo apt-get install htop -y
```

### **Purpose**:
- **`htop`**: A terminal-based system monitor to observe CPU, memory, and processes.

### **Confirm**:
- Run `htop`:
  ```bash
  htop
  ```

---

## **Optional Final Check**
After completing all installations, confirm that all packages are installed:
```bash
dpkg -l | grep -E "build-essential|git|bc|bison|flex|libssl-dev|raspberrypi-kernel-headers|device-tree-compiler|libdrm-dev|libdrm-tests|kmscube|drm-info|fbi|micro|python3|pip3|dkms|htop"
```

---

## **Expected Results**
1. Each installation command completes without errors.
2. Confirmation commands verify the tools and libraries are available.
3. Optional cleanup removes unnecessary packages:
   ```bash
   sudo apt autoremove
   ```

## **Update and Restsart**   
   ```
   sudo apt update && sudo apt upgrade -y
   ```
   ```
   sudo reboot
   ```

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

4. You can also setup the debugging stuff
   ```
   drm.debug=0x1f log_buf_len=16M
   ```

5. Save the file and close the editor.

6. Or just run this:
```
echo "your_desired_cmdline_content" | sudo tee /boot/firmware/cmdline.txt > /dev/null
```

### 3: Configure Wi-Fi for Internet Access

1. Create or edit the `wpa_supplicant.conf` file in the **boot** partition.
You can do this from your SSH connection using:
```
sudo micro /etc/wpa_supplicant/wpa_supplicant.conf
```

2. Add the following content(s):
```
country=CA
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
      ssid="poserguru_s24"
      psk="funkstar"
}

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
169.254.55.240 ssh-ed25519
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
   Remote-SSH: Connect to Host...
   ```

4. Select the Raspberry Pi's SSH connection string:
   ```
   nc4@169.254.55.240
   ```

5. Enter the Pi password `1434` in the VS Code search bar.
 
6. Open the repo in VS Code:
   ```

   code .
   ```

7. Close the VS Code instance when you are done.  

# Enabling additional I2C busses on the Pi

1. Edit the Configuration File: Open the config.txt file:
   ```
   sudo micro /boot/firmware/config.txt
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

See the driver README:
```
src/drivers/nc4_ili9488/README.md
```

# Random

## Log Housekeeping

Retain only 10 MB of log data (M, K):
```
sudo journalctl --vacuum-size=15M
```

Remove logs older than 1 hour (h, d, w):
```
sudo journalctl --vacuum-time=6h
```

Remove all logs
```
sudo rm -rf /var/log/journal/*
sudo systemctl restart systemd-journald
```

Check all logs
```
sudo journalctl
```

Check log disk usage
```
sudo journalctl --disk-usage
```


## WiFi

Check what network we are on:
```
iwgetid -r
```

Disconnect from network:
```
sudo nmcli dev disconnect wlan0
```

Rescan for Networks:
```
sudo nmcli dev wifi rescan
nmcli dev wifi list
```

Connect to one of the wifi networks:
```
sudo nmcli dev wifi connect "NC4_Neurogenesis_Exposure" password "nc4lab1434"
```
```
sudo nmcli dev wifi connect "poserguru_s24" password "funkstar"
```

Varify
```
nmcli connection show --active
```

## Git:

Corrupt Recovery:
```
cd /home/nc4
sudo rm -r TouchscreenApparatus_backup
sudo cp -r ~/TouchscreenApparatus ~/TouchscreenApparatus_backup
diff -r --exclude='.lgd-nfy0' /home/nc4/TouchscreenApparatus /home/nc4/TouchscreenApparatus_backup
cd /home/nc4/TouchscreenApparatus
rm -f .git/objects/*/*
git fetch origin main
git fetch --depth=1
git reset --hard origin/main
sudo cp -r ../TouchscreenApparatus_backup/* .
git add .
git commit -m "Restoring local changes after fixing Git corruption"
git push
```

Merge conflict
```
git pull --no-rebase
```

## System Recovery

### Back up your /boot directory and /lib/modules using:
```
sudo cp -r /boot /boot_backup
sudo cp -r /lib/modules /lib/modules_backup
```

### Clone Pi System to Another SD

1. Download and install `balenaEtcher`
```
https://etcher.balena.io/#download-etcher
```

2. Insert the SD cards you are cloning from and to

3. Select `Clone Drive`

4. Choose the card to clone from and click `Select 1`

5. Select `Select Traget`

6. Choose the card to clone to and click `Select 1`

7. Click `Flash!`


### Image Pi System on Windows

1. Download USB Image Tool
```
https://www.alexpage.de/usb-image-tool/download/
```

2. Extract and run the exe.

3. Insert SD into a reader.

4. Select it in the left pannel of the UI.

5. Click backup.

6. Name it something like `Pi_4_Backup_24_12_29`

7. Click Save.


