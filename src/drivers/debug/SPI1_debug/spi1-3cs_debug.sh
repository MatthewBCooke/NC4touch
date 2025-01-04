#!/bin/bash

# Define the suffix for saved files
SUFFIX="nospi0_kmshack_delayspi1"

# Define the output directory and file names with the suffix
OUTPUT_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug"
OUTPUT_FILE="$OUTPUT_DIR/spi1-3cs_debug_${SUFFIX}.log"
DTS_FILE="$OUTPUT_DIR/live_device_tree_${SUFFIX}.dts"

# Ensure the output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Output directory does not exist. Creating: $OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
fi

# Start writing to the log file
echo "=== SPI1 Debugging Logs ===" > "$OUTPUT_FILE"
echo "Timestamp: $(date)" >> "$OUTPUT_FILE"
echo >> "$OUTPUT_FILE"

# List active (non-commented) lines in config.txt
echo "=== Active Commands in config.txt ===" >> "$OUTPUT_FILE"
CONFIG_FILE="/boot/firmware/config.txt"

if [ -f "$CONFIG_FILE" ]; then
  grep -E '^[^#]' "$CONFIG_FILE" >> "$OUTPUT_FILE"
else
  echo "$CONFIG_FILE not found. Cannot list active commands." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check kernel logs for overlay application errors
echo "=== Kernel Logs: Overlay Loading Errors ===" >> "$OUTPUT_FILE"
dmesg | grep -i "overlay\|dtdebug\|spi\|ili9488" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Capture full dmesg logs for comprehensive review
echo "=== Full Kernel Logs ===" >> "$OUTPUT_FILE"
dmesg >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Decompile live Device Tree
echo "=== Decompiled Device Tree ===" >> "$OUTPUT_FILE"
sudo dtc -I fs -O dts -o "$DTS_FILE" /proc/device-tree
if [ -f "$DTS_FILE" ]; then
  echo "Decompiled device tree saved to: $DTS_FILE" >> "$OUTPUT_FILE"
else
  echo "Failed to decompile live device tree." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check for SPI nodes in the live Device Tree
echo "=== SPI Nodes in Live Device Tree ===" >> "$OUTPUT_FILE"
grep -E "spidev|spi" "$DTS_FILE" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Extract specific spidev references
echo "=== Specific Spidev References in Live Device Tree ===" >> "$OUTPUT_FILE"
grep -A 5 -B 5 "spidev@" "$DTS_FILE" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Extract symbolic links for spidev
echo "=== Symbolic Links for Spidev Nodes ===" >> "$OUTPUT_FILE"
grep -i "spidev" "$DTS_FILE" | grep "=" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Verify if both overlays are loaded at boot
echo "=== Verifying Boot-Time Overlays ===" >> "$OUTPUT_FILE"
if grep -q "spi1-3cs" "$DTS_FILE"; then
  echo "spi1-3cs overlay is successfully loaded." >> "$OUTPUT_FILE"
else
  echo "spi1-3cs overlay is missing in the device tree." >> "$OUTPUT_FILE"
fi
if grep -q "nc4_ili9488" "$DTS_FILE"; then
  echo "nc4_ili9488 overlay is successfully loaded." >> "$OUTPUT_FILE"
else
  echo "nc4_ili9488 overlay is missing in the device tree." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check GPIO configurations
echo "=== GPIO States ===" >> "$OUTPUT_FILE"
if command -v raspi-gpio &> /dev/null; then
  raspi-gpio get >> "$OUTPUT_FILE" 2>&1
else
  echo "raspi-gpio command not found. Skipping GPIO state verification." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check loaded overlays using vcdbg
echo "=== vcdbg Logs for Overlays ===" >> "$OUTPUT_FILE"
if command -v vcdbg &> /dev/null; then
  vcdbg log msg |& grep -i "overlay" >> "$OUTPUT_FILE" 2>&1
else
  echo "vcdbg command not found. Skipping overlay verification with vcdbg." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Runtime overlay application
echo "=== Runtime Overlay Application Logs ===" >> "$OUTPUT_FILE"
echo "Applying spi1-3cs overlay:" >> "$OUTPUT_FILE"
sudo dtoverlay spi1-3cs >> "$OUTPUT_FILE" 2>&1
echo "Applying nc4_ili9488 overlay:" >> "$OUTPUT_FILE"
sudo dtoverlay nc4_ili9488 >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Log available SPI devices
echo "=== Available SPI Devices ===" >> "$OUTPUT_FILE"
ls /dev/spi* >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Summary of results
echo "Debug information saved to: $OUTPUT_FILE"