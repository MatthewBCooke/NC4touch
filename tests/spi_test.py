import spidev

def test_spi(bus, device):
    spi = spidev.SpiDev()
    spi.open(bus, device)
    spi.max_speed_hz = 500000

    print(f"Testing SPI device /dev/spidev{bus}.{device}...")
    response = spi.xfer2([0xAA])
    print(f"Response: {response}")

    spi.close()

def main():
    for bus in [0, 10]:  # Test bus 0 and 10
        for device in [0, 1]:  # Test devices 0 and 1
            try:
                test_spi(bus, device)
            except FileNotFoundError:
                print(f"/dev/spidev{bus}.{device} not found.")
            except Exception as e:
                print(f"Error testing /dev/spidev{bus}.{device}: {e}")

if __name__ == "__main__":
    main()
