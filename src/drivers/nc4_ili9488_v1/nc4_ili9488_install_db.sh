#!/bin/bash

MODULE_NAME="nc4_ili9488"
LOG_KEY="nc4_ili9488"
MODULE_PATH="$(pwd)/${MODULE_NAME}.ko"

echo "=== Cleaning build artifacts ==="
make -C /lib/modules/$(uname -r)/build M=$(pwd) clean

echo "=== Building kernel module ==="
make -C /lib/modules/$(uname -r)/build M=$(pwd) modules

if [ ! -f "${MODULE_PATH}" ]; then
    echo "Error: Module ${MODULE_NAME}.ko not found after build!"
    exit 1
fi

echo "=== Unloading module if loaded ==="
if lsmod | grep -q "${MODULE_NAME}"; then
    sudo rmmod "${MODULE_NAME}" || {
        echo "Error: Failed to unload module ${MODULE_NAME}"
        exit 1
    }
else
    echo "Module ${MODULE_NAME} is not currently loaded."
fi

echo "=== Cleaning up SPI devices ==="
SPI_DEVICES=$(ls /sys/bus/spi/devices/)
if [ -n "${SPI_DEVICES}" ]; then
    echo "Found SPI devices: ${SPI_DEVICES}"
else
    echo "No SPI devices found."
fi

echo "=== Checking device tree nodes ==="
DT_MATCH=$(dtc -I fs /proc/device-tree | grep -i "${MODULE_NAME}")
if [ -n "${DT_MATCH}" ]; then
    echo "Found matching device tree nodes:"
    echo "${DT_MATCH}"
else
    echo "No matching device tree nodes found for ${MODULE_NAME}."
fi

echo "=== Loading module ${MODULE_NAME} ==="
sudo insmod "${MODULE_PATH}" || {
    echo "Error: Failed to load module ${MODULE_NAME}"
    exit 1
}

echo "=== Checking kernel logs for ${LOG_KEY} ==="
dmesg | grep -i "${LOG_KEY}"

echo "=== SPI Devices After Load ==="
SPI_DEVICES=$(ls /sys/bus/spi/devices/)
if [ -n "${SPI_DEVICES}" ]; then
    echo "Found SPI devices after module load: ${SPI_DEVICES}"
else
    echo "No SPI devices found after loading the module."
fi

echo "=== Done ==="
