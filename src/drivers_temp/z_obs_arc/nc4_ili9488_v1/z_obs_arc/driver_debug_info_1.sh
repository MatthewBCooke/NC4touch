#!/bin/bash

OUTPUT_FILE="driver_debug_info.log"

echo "==== Collecting Debugging Information ====" > $OUTPUT_FILE

# Kernel version and configuration
echo "==== Kernel Version ====" >> $OUTPUT_FILE
uname -r >> $OUTPUT_FILE
echo >> $OUTPUT_FILE

echo "==== Kernel Configuration ====" >> $OUTPUT_FILE
if [ -f /proc/config.gz ]; then
    zgrep -E "CONFIG_DRM|CONFIG_MIPI_DBI" /proc/config.gz >> $OUTPUT_FILE
else
    echo "Kernel config not found in /proc/config.gz" >> $OUTPUT_FILE
fi
echo >> $OUTPUT_FILE

# Module dependencies
echo "==== Module Dependencies ====" >> $OUTPUT_FILE
modinfo /lib/modules/$(uname -r)/extra/nc4_ili9488.ko >> $OUTPUT_FILE 2>&1
echo >> $OUTPUT_FILE

# Loaded kernel modules
echo "==== Loaded Kernel Modules ====" >> $OUTPUT_FILE
lsmod | grep -E "drm|mipi_dbi|nc4_ili9488" >> $OUTPUT_FILE
echo >> $OUTPUT_FILE

# Exported symbols in the kernel
echo "==== Exported Symbols ====" >> $OUTPUT_FILE
grep -r "EXPORT_SYMBOL" /usr/src/linux-headers-$(uname -r) | grep -E "mipi_dbi|drm_gem_fb" >> $OUTPUT_FILE 2>/dev/null || echo "No matching symbols found." >> $OUTPUT_FILE
echo >> $OUTPUT_FILE

# DRM Debugging Information
echo "==== DRM Debugging Information ====" >> $OUTPUT_FILE
if [ -d /sys/kernel/debug/dri ]; then
    echo "DebugFS DRM directory exists." >> $OUTPUT_FILE
    ls /sys/kernel/debug/dri/ >> $OUTPUT_FILE
else
    echo "DebugFS DRM directory does not exist." >> $OUTPUT_FILE
fi
echo >> $OUTPUT_FILE

# dmesg logs
echo "==== dmesg Logs (DRM Related) ====" >> $OUTPUT_FILE
dmesg | grep -i drm >> $OUTPUT_FILE
echo >> $OUTPUT_FILE

# Module insertion attempt
echo "==== Attempting to Load Module ====" >> $OUTPUT_FILE
sudo rmmod nc4_ili9488 2>/dev/null || echo "Module nc4_ili9488 not loaded, skipping removal." >> $OUTPUT_FILE
sudo insmod /lib/modules/$(uname -r)/extra/nc4_ili9488.ko >> $OUTPUT_FILE 2>&1
if [ $? -ne 0 ]; then
    echo "Module insertion failed." >> $OUTPUT_FILE
else
    echo "Module inserted successfully." >> $OUTPUT_FILE
fi
echo >> $OUTPUT_FILE

# Review logs after module insertion
echo "==== dmesg Logs (After Module Insertion) ====" >> $OUTPUT_FILE
dmesg | tail -n 50 >> $OUTPUT_FILE

# Final message
echo "Debugging information collected in $OUTPUT_FILE"
