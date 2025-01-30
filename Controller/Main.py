# main
import time
import csv
import threading
import queue
import rpi_m0_comm

class MultiPhaseTraining:
    def __init__(self, pi, peripherals, m0_ports):
        self.pi = pi
        self.peripherals = peripherals
        self.m0_ports = m0_ports

        self.is_session_active = False
        self.automatic_activation_count = 0

        self.message_queue = queue.Queue()
        self.listener_stop_flags = {}
        self.m0_threads = {}


    def start_m0_listeners(self):
        for m0_id, port in self.m0_ports.items():
            stop_flag = threading.Event()
            self.listener_stop_flags[m0_id] = stop_flag

            listener = rpi_m0_comm.M0ListenerThread(
                m0_id,
                port,
                stop_flag,
                self.message_queue
            )
            listener.start()
            self.m0_threads[m0_id] = listener

    def stop_m0_listeners(self):
        for m0_id, flag in self.listener_stop_flags.items():
            flag.set()
        for m0_id, t in self.m0_threads.items():
            t.join()
        print("All M0 listeners stopped.")

    def send_m0_command(self, m0_id, command):
        if m0_id not in self.m0_threads:
            print(f"Error: no thread for {m0_id}.")
            return
        self.m0_threads[m0_id].send_command(command)

# Phase 1: HaBituation
    def Habituation(self):

        AUTO_ACTIVATION_LIMIT = 30
        ITI_DURATION = 10

        print("Starting Habituation")
        self.is_session_active = True
        self.automatic_activation_count = 0

        self.start_m0_listeners()

        def start_iti():
            print("Starting ITI...")
            iti_start_time = time.time()

            while time.time() - iti_start_time < ITI_DURATION:
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)

            while self.peripherals['beam_break'].sensor_state == 0:
                print("Beam still broken at end of ITI. Adding 1s delay.")
                time.sleep(1)
                self.peripherals['beam_break'].activate_beam_break()

            print("ITI completed. Next trial can begin.")

        def large_reward():
            if not self.is_session_active:
                return

            beam_broken = False
            beam_unbroken_after_break = False

            self.peripherals['reward_led'].activate()
            self.peripherals['reward'].dispense_reward()
            print("Large reward started, dispensing for 1s...")

            start_time = time.time()
            reward_duration = 1.0  

            while time.time() - start_time < reward_duration:
                if not self.is_session_active:
                    return
                self.peripherals['beam_break'].activate_beam_break()

                if self.peripherals['beam_break'].sensor_state == 0 and not beam_broken:
                    beam_broken = True
                    print("Beam broken during reward dispense.")
                    self.peripherals['reward_led'].deactivate()

                elif beam_broken and self.peripherals['beam_break'].sensor_state == 1:
                    beam_unbroken_after_break = True
                    print("Beam unbroken.")
                    self.peripherals['reward_led'].deactivate()
                    self.peripherals['beam_break'].deactivate_beam_break()
                    break
                time.sleep(0.01)

            if not self.is_session_active:
                return

            self.peripherals['reward'].stop_reward_dispense()

            if not beam_unbroken_after_break:
                print("Waiting for beam to break...")
                while self.peripherals['beam_break'].sensor_state != 0:
                    if not self.is_session_active:
                        return
                    self.peripherals['beam_break'].activate_beam_break()
                    time.sleep(0.01)

                print("Beam broken. Waiting to unbreak.")
                while self.peripherals['beam_break'].sensor_state == 0 and self.is_session_active:
                    self.peripherals['beam_break'].activate_beam_break()
                    time.sleep(0.01)

                self.peripherals['reward_led'].deactivate()

            print("Beam unbroken. Starting ITI.")
            self.peripherals['beam_break'].deactivate_beam_break()
            start_iti()

        def run_trial():
            if not self.is_session_active:
                return
            print(f"Habituation trial #{self.automatic_activation_count + 1}")
            self.peripherals['reward_led'].activate()
            large_reward()
            self.automatic_activation_count += 1

        # Main logic
        try:
            while self.automatic_activation_count < AUTO_ACTIVATION_LIMIT:
                if not self.is_session_active:
                    break
                run_trial()

            print("Habituation training finished.")

        except KeyboardInterrupt:
            print("Habituation training was interrupted by user.")

        finally:
            self.is_session_active = False
            self.stop_m0_listeners()

            self.peripherals['reward_led'].deactivate()
            self.peripherals['reward'].stop_reward_dispense()
            self.peripherals['beam_break'].deactivate_beam_break()
            print("Habituation phase finished.")

# Initial Touch
    def initial_touch_phase(self, csv_file_path):
        print("Starting Initial Touch.")
        self.is_session_active = True
        self.start_m0_listeners()

        trials = self.read_csv(csv_file_path)

        print("Dispensing 1s free reward.")
        self.large_reward(1.0)

        for i, (img0, img1) in enumerate(trials, start=1):
            if not self.is_session_active:
                break

            print(f"\n=== Trial {i}: M0_0 -> {img0}, M0_1 -> {img1} ===")

            # Preload
            self.send_m0_command("M0_0", f"IMG:{img0}")
            self.send_m0_command("M0_1", f"IMG:{img1}")

            # Dispaly
            self.send_m0_command("M0_0", "SHOW")
            self.send_m0_command("M0_1", "SHOW")

            # Touch time out 3 mins
            touched_m0, touched_image = self.wait_for_touch(img0, img1, timeout=180)
            if not touched_m0:
                print("No touch => skipping reward.")
                continue


            print(f"{touched_m0} touched => {touched_image}. BLACKing screens.")
            self.send_m0_command("M0_0", "BLACK")
            self.send_m0_command("M0_1", "BLACK")


            if touched_image == "A01":
                self.large_reward(2.0)
            elif touched_image == "B01":
                self.large_reward(1.0)
            else:
                self.large_reward(1.0)

        self.is_session_active = False
        self.stop_m0_listeners()
        print("Initial Touch finished.")

# Must Touch
    def phase3(self, csv_file_path):
        print("Starting Phase 3.")
        self.is_session_active = True
        self.start_m0_listeners()
        # blakgvadgvflyweghebqlfh

# Must Initiatie
    def phase4(self, csv_file_path):
        print("Starting Phase 4.")
        self.is_session_active = True
        self.start_m0_listeners()

        #khjdfrgblh


    def read_csv(self, csv_file_path):
        trials = []
        try:
            with open(csv_file_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        trials.append(row)
        except Exception as e:
            print(f"Error reading CSV '{csv_file_path}': {e}")
        return trials

    def wait_for_touch(self, img0, img1, timeout=180):
        start_time = time.time()
        touched_m0 = None
        touched_image = None

        while time.time() - start_time < timeout:
            if not self.is_session_active:
                break
            try:
                m0_id, line = self.message_queue.get(timeout=0.5)
                if line.startswith("TOUCH:"):
                    if m0_id == "M0_0":
                        touched_m0 = "M0_0"
                        touched_image = img0
                    else:
                        touched_m0 = "M0_1"
                        touched_image = img1
                    break
            except queue.Empty:
                pass

        return touched_m0, touched_image

    def large_reward(self, pump_secs=1.0):
        if not self.is_session_active:
            return

        print(f"large_reward: pumping for {pump_secs} seconds.")
        beam_broken = False

        self.peripherals['reward_led'].activate()
        self.peripherals['beam_break'].deactivate_beam_break()

        self.peripherals['reward'].dispense_reward()
        start_t = time.time()

        while (time.time() - start_t) < pump_secs:
            if not self.is_session_active:
                break

            self.peripherals['beam_break'].activate_beam_break()
            if self.peripherals['beam_break'].sensor_state == 0 and not beam_broken:
                beam_broken = True
                print("Beam broken during reward dispense.")
                self.peripherals['reward_led'].deactivate()
            time.sleep(0.01)

        self.peripherals['reward'].stop_reward_dispense()

        if not beam_broken and self.is_session_active:
            print("Waiting for beam to be broken.")
            while self.peripherals['beam_break'].sensor_state != 0:
                if not self.is_session_active:
                    break
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)

            print("Beam broken.")
            while self.peripherals['beam_break'].sensor_state == 0 and self.is_session_active:
                self.peripherals['beam_break'].activate_beam_break()
                time.sleep(0.01)

        self.peripherals['reward_led'].deactivate()
        self.peripherals['beam_break'].deactivate_beam_break()
        print("Beam break deactivated. Reward finished.")

    def stop_session(self):
        if self.is_session_active:
            print("Forcing session to stop.")
            self.is_session_active = False
            for m0_id in self.m0_ports:
                self.send_m0_command(m0_id, "BLACK")
            self.stop_m0_listeners()

