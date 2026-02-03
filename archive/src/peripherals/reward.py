import pigpio
import time

class Reward:
    def __init__(self, pi, pin):
        self.pi = pi
        self.pin = pin
        self.is_priming = False
        self.reward_duration_ms = 1000

    def setup_reward(self):
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.pi.set_PWM_range(self.pin, 255)
        self.pi.set_PWM_frequency(self.pin, 5000)  # Match frequency from Arduino code

    def dispense_reward(self):
        self.pi.set_PWM_dutycycle(self.pin, 255)

    def stop_reward_dispense(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)

    def prime_feeding_tube(self):
        self.is_priming = True
        start_time = time.time()

        while self.is_priming and (time.time() - start_time) < 120:
            self.pi.set_PWM_dutycycle(self.pin, 255)  # Full power

            command = input("Enter 'x' to stop priming: ")
            if command == 'x':
                self.stop_priming()
                break

            time.sleep(0.1) 

        self.pi.set_PWM_dutycycle(self.pin, 0)
        if self.is_priming:
            print("Priming Finished")

    def stop_priming(self):
        self.pi.set_PWM_dutycycle(self.pin, 0)
        self.is_priming = False
        print("Priming stopped")
