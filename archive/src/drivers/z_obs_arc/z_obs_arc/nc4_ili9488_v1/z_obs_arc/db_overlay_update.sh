#!/bin/bash

OVERLAY_NAME="test_overlay"
OVERLAY_DTS="${OVERLAY_NAME}.dts"
OVERLAY_DTBO="${OVERLAY_NAME}.dtbo"
OVERLAY_DIR="/boot/overlays"

echo "=== Starting Overlay Update Process ==="

# Check if the DTS file exists
if [ ! -f "${OVERLAY_DTS}" ]; then
    echo "Error: DTS file '${OVERLAY_DTS}' not found in the current directory!"
    exit 1
fi
echo "Found DTS file: ${OVERLAY_DTS}"

# Compile the DTS file into a DTBO
echo "Compiling ${OVERLAY_DTS} into ${OVERLAY_DTBO}..."
if ! dtc -@ -I dts -O dtb -o "${OVERLAY_DTBO}" "${OVERLAY_DTS}"; then
    echo "Error: Failed to compile ${OVERLAY_DTS} into ${OVERLAY_DTBO}!"
    exit 1
fi
echo "Successfully compiled ${OVERLAY_DTBO}"

# Copy the DTBO file to the overlays directory
echo "Copying ${OVERLAY_DTBO} to ${OVERLAY_DIR}..."
if ! sudo cp "${OVERLAY_DTBO}" "${OVERLAY_DIR}/"; then
    echo "Error: Failed to copy ${OVERLAY_DTBO} to ${OVERLAY_DIR}!"
    exit 1
fi
echo "Successfully copied ${OVERLAY_DTBO} to ${OVERLAY_DIR}"

# Apply the overlay dynamically
echo "Applying the overlay ${OVERLAY_NAME}..."
if ! sudo dtoverlay "${OVERLAY_NAME}"; then
    echo "Error: Failed to apply overlay '${OVERLAY_NAME}'!"
    exit 1
fi
echo "Overlay '${OVERLAY_NAME}' successfully applied."

# Verify if the overlay is applied
echo "Verifying if the overlay is active..."
if sudo dtc -I fs /proc/device-tree | grep -q "${OVERLAY_NAME}"; then
    echo "Overlay '${OVERLAY_NAME}' is active."
else
    echo "Warning: Overlay '${OVERLAY_NAME}' does not appear to be active."
    echo "Please verify the device tree and system logs."
fi

echo "=== Overlay Update Process Completed ==="
