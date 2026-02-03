import smbus
import time

class I2CUtils:
    def __init__(self):
        self.i2c_allow = False
        self.is_training_active = False
        self.n_devices = 0
        self.i2c_addr = []
        self.img_id = 1
        self.resp = 0
        self.CMD_SHOW = 6
        self.CMD_BLACK = 3
        self.CMD_RESET = 4
        self.CMD_IMG = 5
        self.RIGHT_M0_ADDR = 0x04  
        self.LEFT_M0_ADDR = 0x14   
        self.dir_str = ['L', 'R']
        self.correct_dir = None
        self.bus = smbus.SMBus(1)  # 1 indicates /dev/i2c-1

    def setup_i2c(self):
        self.i2c_allow = True
        self.i2c_scanner()

    def i2c_scanner(self):
        print("Scanning for I2C devices...")
        self.n_devices = 0
        for address in range(0x03, 0x78):
            try:
                self.bus.write_quick(address)
                print(f"I2C device found at address 0x{address:02X}!")
                self.i2c_addr.append(address)
                self.n_devices += 1
            except IOError:
                pass  # Address is not in use
        if self.n_devices == 0:
            print("No I2C devices found")
        else:
            print("Scanning complete")

    def receive_event(self):
        try:
            data = self.bus.read_byte(self.RIGHT_M0_ADDR)  
            print(f"Received data: {data}")
        except Exception as e:
            print(f"Error receiving event: {e}")

    def send_cmd(self, cmd, m0_id):
        try:
            self.bus.write_byte(m0_id, cmd)
            print(f"Command {cmd} sent to device {m0_id}")
        except Exception as e:
            print(f"Failed to send command: {e}")

    def response_from_right_m0(self):
        self.resp = 0x00
        while self.resp == 0x00:
            try:
                self.resp = self.bus.read_byte(self.RIGHT_M0_ADDR)
                time.sleep(0.005)
                print("Acknowledgment from Right M0")
            except IOError:
                pass  

    def response_from_left_m0(self):
        self.resp = 0x00
        while self.resp == 0x00:
            try:
                self.resp = self.bus.read_byte(self.LEFT_M0_ADDR)
                time.sleep(0.01)
                print("Acknowledgment from Left M0")
            except IOError:
                pass 

    def send_black_to_all_m0s(self):
        for address in self.i2c_addr:
            self.send_black(address)
            # Wait for acknowledgment
            self.resp = 0x00
            while self.resp == 0x00:
                try:
                    self.resp = self.bus.read_byte(address)
                    time.sleep(0.01)
                    print(f"Black Response from M0 at address {address}")
                except IOError:
                    pass  # Keep waiting for acknowledgment

    def send_image_to_m0(self, img_id_str, m0_id):
        img_data = [ord(char) for char in img_id_str]
        try:
            self.bus.write_i2c_block_data(m0_id, self.CMD_IMG, img_data)
            print(f"Image ID '{img_id_str}' sent to M0 {m0_id}")
        except Exception as e:
            print(f"Failed to send image: {e}")

    def send_black(self, m0_id):
        self.send_cmd(self.CMD_BLACK, m0_id)

    def stop(self):
        self.bus.close()
