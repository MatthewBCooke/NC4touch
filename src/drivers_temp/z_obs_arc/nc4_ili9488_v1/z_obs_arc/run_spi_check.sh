#!/bin/bash

# Base directory for SPI devices
SPI_BASE_DIR="/sys/bus/spi/devices"

# Check if the SPI base directory exists
if [ ! -d "$SPI_BASE_DIR" ]; then
  echo "SPI base directory does not exist: $SPI_BASE_DIR"
  exit 1
fi

# Function to check SPI mode from dmesg
check_spi_mode() {
  local device=$1
  local spi_index=$(basename "$device")
  echo "Checking SPI mode for $spi_index (from dmesg):"
  dmesg | grep "$spi_index" | grep "SPI init successful" | awk -F'mode=' '{print $2}' | awk '{print $1}'
}

# Iterate through each SPI device
for DEVICE in "$SPI_BASE_DIR"/*; do
  echo "Inspecting SPI device: $DEVICE"
  
  # List the top-level contents of the device directory
  echo "Top-level contents:"
  ls -l "$DEVICE"

  # Explore relevant subdirectories if they exist
  for SUBDIR in "drm" "graphics" "power" "statistics"; do
    if [ -d "$DEVICE/$SUBDIR" ]; then
      echo "Contents of $DEVICE/$SUBDIR:"
      ls -l "$DEVICE/$SUBDIR"
    fi
  done

  # Inspect runtime statistics if available
  if [ -d "$DEVICE/statistics" ]; then
    echo "Runtime statistics for $DEVICE:"
    for STAT_FILE in "$DEVICE/statistics"/*; do
      echo "$(basename "$STAT_FILE"): $(cat "$STAT_FILE")"
    done
  fi

  # Inspect power management status
  if [ -d "$DEVICE/power" ]; then
    echo "Power management status for $DEVICE:"
    if [ -f "$DEVICE/power/runtime_status" ]; then
      echo "Runtime status: $(cat "$DEVICE/power/runtime_status")"
    fi
    if [ -f "$DEVICE/power/autosuspend_delay_ms" ]; then
      echo "Autosuspend delay (ms): $(cat "$DEVICE/power/autosuspend_delay_ms")"
    fi
  fi

  # Inspect device tree node if available
  if [ -L "$DEVICE/of_node" ]; then
    OF_NODE=$(readlink -f "$DEVICE/of_node")
    echo "Inspecting device tree node: $OF_NODE"
    ls -l "$OF_NODE"
    for DT_FILE in "$OF_NODE"/*; do
      echo "$(basename "$DT_FILE"): $(cat "$DT_FILE")"
    done
  fi

  # Check and print SPI mode from dmesg logs
  SPI_MODE=$(check_spi_mode "$DEVICE")
  if [ -n "$SPI_MODE" ]; then
    echo "SPI mode: $SPI_MODE"
  else
    echo "SPI mode: Not found in dmesg logs"
  fi

  echo "-------------------------------------------"
done

echo "Completed inspecting all SPI devices."
