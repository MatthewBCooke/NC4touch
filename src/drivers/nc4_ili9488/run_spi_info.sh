#!/bin/bash

# Define output directory
OUTPUT_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug"
mkdir -p "$OUTPUT_DIR"

# Check SPI-related kernel modules
echo "Checking loaded SPI-related kernel modules..." > "$OUTPUT_DIR/spi_modules.txt"
lsmod | grep spi >> "$OUTPUT_DIR/spi_modules.txt"

# Check Device Tree for SPI and spidev nodes
echo "Dumping Device Tree related to SPI..." > "$OUTPUT_DIR/spi_dts.txt"
dtc -I fs /proc/device-tree > "$OUTPUT_DIR/device_tree.dts"

# Search for spidev references in the active Device Tree
echo "Searching for spidev references..." >> "$OUTPUT_DIR/spi_dts.txt"
grep -i spidev "$OUTPUT_DIR/device_tree.dts" >> "$OUTPUT_DIR/spi_dts.txt"

# Check for enabled SPI nodes
echo "Checking enabled SPI nodes..." > "$OUTPUT_DIR/spi_nodes.txt"
for spi in /proc/device-tree/soc/*spi*/status; do
    echo "$spi: $(cat $spi)" >> "$OUTPUT_DIR/spi_nodes.txt"
done

# Kernel log analysis for SPI and spidev
echo "Extracting kernel log entries related to SPI and spidev..." > "$OUTPUT_DIR/dmesg_spi.txt"
dmesg | grep -i "spi\|spidev" >> "$OUTPUT_DIR/dmesg_spi.txt"

# List /dev/spidev* devices
echo "Listing /dev/spidev* devices..." > "$OUTPUT_DIR/spidev_devices.txt"
ls /dev/spidev* >> "$OUTPUT_DIR/spidev_devices.txt" 2>/dev/null || echo "No spidev devices found" >> "$OUTPUT_DIR/spidev_devices.txt"

echo "System SPI debug information has been saved to $OUTPUT_DIR"
