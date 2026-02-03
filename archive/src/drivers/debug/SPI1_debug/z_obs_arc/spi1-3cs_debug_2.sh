#!/bin/bash

# Define the output directory and file
OUTPUT_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug"
OUTPUT_FILE="$OUTPUT_DIR/spi1-3cs_debug_2.log"

# Ensure the output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Output directory does not exist. Creating: $OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
fi

# Start writing to the log file
echo "=== SPI1 Debugging Logs: Boot-Time Loading ===" > "$OUTPUT_FILE"
echo "Timestamp: $(date)" >> "$OUTPUT_FILE"
echo >> "$OUTPUT_FILE"

# Check kernel logs for overlay application
echo "=== Kernel Logs: Overlay Loading Errors ===" >> "$OUTPUT_FILE"
dmesg | grep -i "overlay\|dtdebug\|spi\|ili9488" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Capture full dmesg logs for further review
echo "=== Full Kernel Logs ===" >> "$OUTPUT_FILE"
dmesg >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Decompile the live Device Tree
echo "=== Decompiled Device Tree ===" >> "$OUTPUT_FILE"
DTS_FILE="$OUTPUT_DIR/merged_device_tree.dts"
sudo dtc -I fs -O dts -o "$DTS_FILE" /proc/device-tree
if [ -f "$DTS_FILE" ]; then
  echo "Decompiled device tree saved to: $DTS_FILE" >> "$OUTPUT_FILE"
else
  echo "Failed to decompile live device tree." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Verify SPI nodes in the live device tree
echo "=== SPI Nodes in Live Device Tree ===" >> "$OUTPUT_FILE"
grep -E "spidev|spi" "$DTS_FILE" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Verify specific spidev references
echo "=== Specific Spidev References in Live Device Tree ===" >> "$OUTPUT_FILE"
grep -A 5 -B 5 "spidev@" "$DTS_FILE" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Verify symbolic links for spidev
echo "=== Symbolic Links for Spidev Nodes ===" >> "$OUTPUT_FILE"
grep -i "spidev" "$DTS_FILE" | grep "=" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Summary of results
echo "Debugging information saved to: $OUTPUT_FILE"
