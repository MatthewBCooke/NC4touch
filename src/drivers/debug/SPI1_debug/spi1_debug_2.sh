#!/bin/bash

# Define the output directory and file
OUTPUT_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/SPI1_debug"
OUTPUT_FILE="$OUTPUT_DIR/spi1_debug_2.log"

# Ensure the output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Output directory does not exist. Creating: $OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
fi

# Start writing to the log file
echo "=== SPI1 Debug Step 2: Additional Checks ===" > "$OUTPUT_FILE"
echo "Timestamp: $(date)" >> "$OUTPUT_FILE"
echo >> "$OUTPUT_FILE"

# Check kernel logs for overlay application errors
echo "=== Kernel Logs: Overlay Loading Errors ===" >> "$OUTPUT_FILE"
dmesg | grep -i "overlay\|dtdebug\|spi\|ili9488" >> "$OUTPUT_FILE" 2>&1
echo >> "$OUTPUT_FILE"

# Verify live Device Tree for SPI nodes
echo "=== Live Device Tree: SPI Nodes ===" >> "$OUTPUT_FILE"
if [ -d "/proc/device-tree/soc/spi@7e215080" ]; then
  echo "Contents of /proc/device-tree/soc/spi@7e215080:" >> "$OUTPUT_FILE"
  ls /proc/device-tree/soc/spi@7e215080 >> "$OUTPUT_FILE" 2>&1
else
  echo "/proc/device-tree/soc/spi@7e215080 directory not found." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check loaded overlays using vcdbg (if available)
echo "=== vcdbg Logs for Overlays ===" >> "$OUTPUT_FILE"
if command -v vcdbg &> /dev/null; then
  vcdbg log msg |& grep -i "overlay" >> "$OUTPUT_FILE" 2>&1
else
  echo "vcdbg command not found. Skipping overlay verification with vcdbg." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Verify GPIO configurations
echo "=== GPIO States ===" >> "$OUTPUT_FILE"
if command -v raspi-gpio &> /dev/null; then
  raspi-gpio get >> "$OUTPUT_FILE" 2>&1
else
  echo "raspi-gpio command not found. Skipping GPIO state verification." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check DRM devices and framebuffers
echo "=== DRM Cards and Framebuffers ===" >> "$OUTPUT_FILE"
if [ -d "/sys/class/drm" ]; then
  ls /sys/class/drm >> "$OUTPUT_FILE" 2>&1
else
  echo "/sys/class/drm directory not found. Skipping DRM card check." >> "$OUTPUT_FILE"
fi
if [ -d "/sys/class/graphics" ]; then
  ls /sys/class/graphics >> "$OUTPUT_FILE" 2>&1
else
  echo "/sys/class/graphics directory not found. Skipping framebuffer check." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check for driver module loading issues
echo "=== Driver Module and Kernel Symbol Check ===" >> "$OUTPUT_FILE"
DRIVER_PATH="/lib/modules/$(uname -r)/extra/nc4_ili9488.ko"
if [ -f "$DRIVER_PATH" ]; then
  echo "Driver module found: $DRIVER_PATH" >> "$OUTPUT_FILE"
  echo "Checking for unresolved symbols:" >> "$OUTPUT_FILE"
  modinfo "$DRIVER_PATH" >> "$OUTPUT_FILE" 2>&1
else
  echo "Driver module not found: $DRIVER_PATH" >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Check system firmware and kernel versions
echo "=== Firmware and Kernel Versions ===" >> "$OUTPUT_FILE"
vcgencmd version >> "$OUTPUT_FILE" 2>&1 || echo "vcgencmd command not available." >> "$OUTPUT_FILE"
uname -a >> "$OUTPUT_FILE"
echo >> "$OUTPUT_FILE"

# Check available Device Tree sources
echo "=== Device Tree Source Directory ===" >> "$OUTPUT_FILE"
if [ -d "/boot/firmware/overlays" ]; then
  ls /boot/firmware/overlays | grep -i "nc4_ili9488" >> "$OUTPUT_FILE" 2>&1
else
  echo "/boot/firmware/overlays directory not found. Skipping overlay source check." >> "$OUTPUT_FILE"
fi
echo >> "$OUTPUT_FILE"

# Summary of results
echo "Debug information saved to: $OUTPUT_FILE"
