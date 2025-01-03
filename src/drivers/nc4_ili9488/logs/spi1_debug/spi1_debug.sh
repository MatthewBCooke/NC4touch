#!/bin/bash

# Define the output directory and file
OUTPUT_DIR="/home/nc4/TouchscreenApparatus/src/drivers/nc4_ili9488/logs"
OUTPUT_FILE="$OUTPUT_DIR/spi1_debug.log"

# Ensure the output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Output directory does not exist. Creating: $OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
fi

# Start writing to the log file
echo "=== SPI1 Debug Information ===" > "$OUTPUT_FILE"
echo "Timestamp: $(date)" >> "$OUTPUT_FILE"
echo >> "$OUTPUT_FILE"

# Collect dmesg logs related to Device Tree and DRM
echo "=== dmesg Logs ===" >> "$OUTPUT_FILE"
dmesg | grep -i "dtdebug\|overlay\|spi\|ili9488" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Check loaded overlays using vcdbg
echo "=== Loaded Overlays ===" >> "$OUTPUT_FILE"
if command -v vcdbg &> /dev/null; then
  vcdbg log msg |& grep -i "overlay" >> "$OUTPUT_FILE" 2>&1
else
  echo "vcdbg command not found. Skipping." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Inspect live Device Tree for SPI nodes
echo "=== Live Device Tree (/proc/device-tree) ===" >> "$OUTPUT_FILE"
if [ -d "/proc/device-tree" ]; then
  echo "/soc/spi@7e215080:" >> "$OUTPUT_FILE"
  ls /proc/device-tree/soc/spi@7e215080 >> "$OUTPUT_FILE" 2>&1
else
  echo "/proc/device-tree directory not found. Skipping." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# List GPIO states
echo "=== GPIO States ===" >> "$OUTPUT_FILE"
if command -v raspi-gpio &> /dev/null; then
  raspi-gpio get >> "$OUTPUT_FILE" 2>&1
else
  echo "raspi-gpio command not found. Skipping." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# List kernel modules for DRM and SPI
echo "=== Loaded Kernel Modules ===" >> "$OUTPUT_FILE"
lsmod | grep -E "drm|spi" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Verify existence of nc4_ili9488.ko
echo "=== Driver Module Check ===" >> "$OUTPUT_FILE"
DRIVER_PATH="/lib/modules/$(uname -r)/extra/nc4_ili9488.ko"
if [ -f "$DRIVER_PATH" ]; then
  echo "Driver module found: $DRIVER_PATH" >> "$OUTPUT_FILE"
else
  echo "Driver module not found: $DRIVER_PATH" >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check DRM cards and connectors
echo "=== DRM Cards and Connectors ===" >> "$OUTPUT_FILE"
if [ -d "/sys/class/drm" ]; then
  ls /sys/class/drm >> "$OUTPUT_FILE" 2>&1
else
  echo "/sys/class/drm directory not found. Skipping." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# List framebuffers
echo "=== Framebuffers ===" >> "$OUTPUT_FILE"
if [ -d "/sys/class/graphics" ]; then
  ls /sys/class/graphics >> "$OUTPUT_FILE" 2>&1
else
  echo "/sys/class/graphics directory not found. Skipping." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Summary of results
echo "Debug information saved to: $OUTPUT_FILE"
