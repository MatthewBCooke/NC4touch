echo "==== START: Setting Up Device Tree Overlay ===="
# Define directory for overlay
DT_OVERLAY_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488"
cd "$DT_OVERLAY_DIR"

# Compile the overlay file with robust warnings
sudo dtc -@ -f -I dts -O dtb -Wunit_address_vs_reg -Wavoid_unnecessary_addr_size -o /boot/firmware/overlays/nc4_ili9488.dtbo nc4_ili9488-overlay.dts

# Verify the overlay file was created
if ls /boot/firmware/overlays/*nc4_ili9488* 1>/dev/null 2>&1; then
    echo "Overlay successfully compiled and installed."
else
    echo "Error: Overlay file not found. Compilation failed." >&2
    exit 1
fi

# # Print contents of config.txt for verification
# echo "Contents of /boot/firmware/config.txt:"
# cat /boot/firmware/config.txt

echo "==== Building and Installing the ILI9488 Driver ===="
# Define directory for driver
ILI9488_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488"
cd "$ILI9488_DIR"

# Clean previous builds
echo "Cleaning previous build..."
make clean || true

# Build the driver
echo "Building driver..."
BUILD_LOG="build.log"

# Try plain make first
if make > "$BUILD_LOG" 2>&1; then
    echo "Driver built successfully with plain make."
else
    echo "Plain make failed. Trying kernel build system method..."
    if make -C /lib/modules/$(uname -r)/build M=$PWD > "$BUILD_LOG" 2>&1; then
        echo "Driver built successfully using kernel build system method."
    else
        echo "Error: Driver build failed with both methods." >&2

        # Provide details of the failure
        echo "==== Build Failure Details ===="
        echo "Last 20 lines of build output:"
        tail -n 20 "$BUILD_LOG" || echo "No build log found."

        echo "==== Automated Checks ===="

        # Check kernel headers
        echo "Checking for kernel headers..."
        KERNEL_HEADERS="/lib/modules/$(uname -r)/build"
        if [ -d "$KERNEL_HEADERS" ]; then
            echo "Kernel headers found: $KERNEL_HEADERS"
        else
            echo "Error: Kernel headers for $(uname -r) not installed." >&2
            echo "Install them using: sudo apt-get install linux-headers-$(uname -r)"
            exit 1
        fi

        # Check kernel version mismatch
        echo "Checking kernel version match..."
        MODULE_PATH="nc4_ili9488.ko"
        if [ -f "$MODULE_PATH" ]; then
            VERMAGIC=$(modinfo -F vermagic "$MODULE_PATH" 2>/dev/null || echo "Unavailable")
            CURRENT_KERNEL=$(uname -r)
            if [ "$VERMAGIC" != "$CURRENT_KERNEL" ]; then
                echo "Error: Vermagic ($VERMAGIC) does not match the current kernel ($CURRENT_KERNEL)." >&2
                echo "Ensure you're building against the correct kernel headers."
                exit 1
            else
                echo "Kernel version matches: $CURRENT_KERNEL"
            fi
        else
            echo "Module file not found. Skipping vermagic check."
        fi

        # Check source file syntax
        echo "Checking for syntax errors in source files..."
        if ! gcc -fsyntax-only *.c > /dev/null 2>&1; then
            echo "Error: Syntax errors detected in source files." >&2
            gcc -fsyntax-only *.c 2>&1 | head -n 10
            exit 1
        else
            echo "No syntax errors detected."
        fi

        exit 1
    fi
fi



# Check vermagic for compatibility
echo "Checking vermagic for kernel module..."
VERMAGIC=$(modinfo nc4_ili9488.ko | grep vermagic | awk '{print $2}')
CURRENT_KERNEL=$(uname -r)

if [ "$VERMAGIC" == "$CURRENT_KERNEL" ]; then
    echo "Vermagic matches the current kernel version: $CURRENT_KERNEL"
else
    echo "Error: Vermagic ($VERMAGIC) does not match the current kernel version ($CURRENT_KERNEL)." >&2
    echo "Ensure you are building the module against the correct kernel headers." >&2
    exit 1
fi


# Verify the driver file was created
if [ -f "nc4_ili9488.ko" ]; then
    echo "Driver build successful."
else
    echo "Error: Driver file not found. Build failed." >&2
    exit 1
fi

# Install the driver
echo "Installing driver..."
sudo mkdir -p /lib/modules/$(uname -r)/extra/
sudo cp nc4_ili9488.ko /lib/modules/$(uname -r)/extra/
sudo chmod u=rw,go=r /lib/modules/$(uname -r)/extra/nc4_ili9488.ko
sudo depmod -a

# Verify the driver is available
if sudo modinfo /lib/modules/$(uname -r)/extra/nc4_ili9488.ko; then
    echo "Driver successfully installed."
else
    echo "Error: Driver not recognized by the kernel." >&2
    exit 1
fi

echo "==== Loading the Driver ===="
# Load the driver
if sudo modprobe nc4_ili9488; then
    echo "Driver successfully loaded."
else
    echo "Error: Failed to load the driver." >&2
    exit 1
fi

# Verify the driver is loaded
if lsmod | grep nc4_ili9488; then
    echo "Driver is loaded."
else
    echo "Error: Driver is not loaded." >&2
    exit 1
fi

# Check kernel logs
echo "Checking kernel logs for driver initialization..."
dmesg | grep nc4_ili9488

echo "==== Setup Complete ===="
