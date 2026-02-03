#!/bin/bash
echo "=== I2C Implementation Verification ==="
echo ""
echo "1. Checking file existence..."
files=(
    "Controller/M0DeviceI2C.py"
    "M0Touch_I2C/M0Touch_I2C.ino"
    "Controller/Chamber.py"
    "docs/I2C_IMPLEMENTATION.md"
    "tests/test_i2c.py"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file MISSING"
        all_exist=false
    fi
done

echo ""
echo "2. Line counts..."
wc -l Controller/M0DeviceI2C.py M0Touch_I2C/M0Touch_I2C.ino docs/I2C_IMPLEMENTATION.md tests/test_i2c.py

echo ""
echo "3. Checking Python syntax..."
python3 -m py_compile Controller/M0DeviceI2C.py 2>&1 | head -5
python3 -m py_compile tests/test_i2c.py 2>&1 | head -5

echo ""
echo "4. Checking for placeholders..."
grep -n "TODO\|FIXME\|XXX\|PLACEHOLDER" Controller/M0DeviceI2C.py M0Touch_I2C/M0Touch_I2C.ino tests/test_i2c.py 2>&1 | head -10 || echo "  ✓ No placeholders found"

echo ""
echo "5. Checking for type hints in Python..."
grep -c "def.*->" Controller/M0DeviceI2C.py | xargs -I {} echo "  M0DeviceI2C.py: {} functions with type hints"

echo ""
echo "6. Checking for docstrings..."
grep -c '"""' Controller/M0DeviceI2C.py | xargs -I {} echo "  M0DeviceI2C.py: {} docstrings"

echo ""
echo "=== Verification Complete ==="
