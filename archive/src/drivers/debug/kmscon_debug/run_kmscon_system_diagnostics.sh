#!/bin/bash

# Define the log directory and log file
LOG_DIR="/home/nc4/TouchscreenApparatus/src/drivers/debug/kmscon_debug/logs"
LOG_FILE="${LOG_DIR}/kmscon_system_diagnostics.log"

# Ensure the log directory exists
mkdir -p "$LOG_DIR"

# Begin the consolidated log
echo "KMSCON Debug Logs - $(date)" > "$LOG_FILE"

# Append each command's output to the log file
{
  echo -e "\n=== dmesg DRM Logs ==="
  dmesg | grep -i drm

  echo -e "\n=== kmscon Systemd Logs ==="
  sudo journalctl -u kmsconvt@tty1.service --no-pager

  echo -e "\n=== DRM State (Card 0) ==="
  sudo cat /sys/kernel/debug/dri/0/state

  echo -e "\n=== DRM State (Card 1) ==="
  sudo cat /sys/kernel/debug/dri/1/state

  echo -e "\n=== DRM Devices List ==="
  ls -l /sys/class/drm/

  echo -e "\n=== Card 0 Info ==="
  ls -l /sys/class/drm/card0

  echo -e "\n=== Card 1 Info ==="
  ls -l /sys/class/drm/card1

  echo -e "\n=== Framebuffer Devices ==="
  ls -l /dev/fb*

  echo -e "\n=== Framebuffer Info (fb0) ==="
  sudo fbset -fb /dev/fb0

  echo -e "\n=== Framebuffer Info (fb1) ==="
  sudo fbset -fb /dev/fb1

  echo -e "\n=== Framebuffer Users ==="
  sudo fuser /dev/fb0 /dev/fb1

  echo -e "\n=== Connector Card 0 Status ==="
  cat /sys/class/drm/card0-SPI-1/status

  echo -e "\n=== Connector Card 1 Status ==="
  cat /sys/class/drm/card1-SPI-2/status

  echo -e "\n=== Full dmesg Log ==="
  dmesg

  echo -e "\n=== Recent KMSCON Logs (Last 30 Minutes) ==="
  sudo journalctl --since "30 minutes ago" | grep kmscon

  echo -e "\n=== KMSCON Boot-Only Logs ==="
  sudo journalctl -b | grep kmscon
} >> "$LOG_FILE" 2>&1

echo "Logs have been saved to $LOG_FILE"
