import pigpio
import time
import serial

class Reward:
    def __init__(self, pi, pin, serial_port='/dev/ttyUSB0', baudrate=9600):
        self.pi = pi
        self.pin = pin
        self.is_priming = False
        self.reward_duration_ms = 1000

        try:
            self.serial = serial.Serial(serial_port, baudrate, timeout=0.1)
            print(f"Serial connection established on {serial_port}.")
        except serial.SerialException as e:
            self.serial = None
            print(f"Failed to connect to serial port {serial_port}: {e}")

    def setup_reward(self):
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)  
        self.pi.set_PWM_range(self.pin, 255)   
        self.pi.set_PWM_frequency(self.pin, 5000) 

    def dispense_reward(self):
        print("Dispensing reward.")
        self.pi.set_PWM_dutycycle(self.pin, 255) 
        time.sleep(self.reward_duration_ms / 1000) 
        self.stop_reward_dispense()

    def stop_reward_dispense(self):
        self.pi.set_PWM_dutycycle(self.pin, 0) 
        print("Reward dispensing stopped.")

    def prime_feeding_tube(self):
        self.is_priming = True
        start_time = time.time()

        print("Priming started")
        try:
            while self.is_priming and (time.time() - start_time) < 120:  # 2 minutes
                self.pi.set_PWM_dutycycle(self.pin, 255) 

                if self.serial and self.serial.in_waiting > 0:
                    try:
                        command = self.serial.read().decode('utf-8').strip()
                        if command == 'x':
                            self.stop_priming()
                            break
                    except UnicodeDecodeError:
                        print("Failed to decode serial input.")

                time.sleep(0.1)  

            self.pi.set_PWM_dutycycle(self.pin, 0)  
            if self.is_priming:
                print("Priming finished.")
        except Exception as e:
            self.stop_priming()
            print(f"Error during priming: {e}")

    def stop_priming(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.is_priming = False
        print("Priming stopped.")

    def cleanup(self):
        self.stop_reward_dispense()  
        self.pi.set_PWM_dutycycle(self.pin, 0)
