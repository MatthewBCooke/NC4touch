

# Define the expected nodes
EXPECTED_NODES=(
    "pitft@0"
    "pitft_pins"
    "backlight"
)

# Validate each node in the live device tree
echo "Checking overlay nodes in the live device tree..."
for NODE in "${EXPECTED_NODES[@]}"; do
    NODE_PATH="/proc/device-tree/soc/spi@7e204000/$NODE"
    if [ -d "$NODE_PATH" ] || dtc -I fs /proc/device-tree | grep -q "$NODE"; then
        echo "Node '$NODE' found in the live device tree."
    else
        echo "Node '$NODE' not found. Check overlay or binding for issues."
    fi
done

