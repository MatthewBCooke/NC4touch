# On a Raspberry Pi 4, create initial functions for the project

import smbus

I2C_CHANNEL = 1


# Scan I2C bus for devices
def scan_i2c():
    i2c = smbus.SMBus(I2C_CHANNEL)
    devices = []
    for addr in range(0x03, 0x78):
        try:
            i2c.read_byte(addr)
            devices.append(addr)
        except:
            pass
    return devices

if __name__ == '__main__':
    print(scan_i2c())