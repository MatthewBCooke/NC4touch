# MSRRA

# Setting Up Raspberry Pi OS with SSH and VS Code Remote Development

## 1. Install Raspberry Pi OS
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
   - Plug in the SD card and power on the Pi
   - Open a terminal and run:
   ```
   sudo apt update
   sudo apt full-upgrade -y
   ``` 
   - Reboot:
   ```
   sudo reboot
   ```

## 2. Enable SSH on the Raspberry Pi if needed
1. Boot the Raspberry Pi.
2. Open a terminal on the Pi and run:
   ```bash
   sudo raspi-config
   ```
3. Navigate to:
   - **Interface Options > SSH**
   - Select **Enable**.

## 3. Assign a Static IP and Configure Internet Access for the Raspberry Pi

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
4. When prompted:
   - Type `yes` to continue connecting.
   - Enter the password: `1434`.
5. Verify the connection works, then exit the SSH session:
   ```bash
   exit
   ```

### 6: Verify Internet Access on the Raspberry Pi
1. After connecting via SSH, test the Wi-Fi connection:
   ```
   ping -c 4 google.com
   ```

## 4. Set Up Remote Development in VS Code
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

## 7. Complete the Remote-SSH Setup
1. A new VS Code window will open.
2. When prompted to select the platform, choose:
   ```
   Linux
   ```
3. Enter the password again: `1434`.
4. VS Code will automatically download and set up the remote server on the Raspberry Pi.

## Setup access to GitHub

1. Generate a new SSH key:
   ```
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
   - Replace `your_email@example.com` with your GitHub email.
   - Press `Enter` to accept all defaults and skip passphrase.

2. Copy the public key:
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

5. Clone the repository:
   ```
   git clone git@github.com:NC4Lab/TouchscreenApparatus.git
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
8. Open the repo in VS Code:
   ```
   code .
   ```
9. Close the VS Code instance when you are done.  