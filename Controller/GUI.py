import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit,
    QFileDialog, QGroupBox, QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt

import pigpio
from LED import LED
from Reward import Reward
from BeamBreak import BeamBreak

import rpi_m0_comm
import Main  


class MultiTrialGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NC4Touch GUI")
        self.setGeometry(300, 100, 1000, 600)

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        self.is_training = False
        self.is_priming = False


        top_layout = QHBoxLayout()
        self.discover_button = QPushButton("Discover M0 Boards")
        self.discover_button.clicked.connect(self.on_discover)
        top_layout.addWidget(self.discover_button)
        self.main_layout.addLayout(top_layout)


        self.init_mouse_info_ui()

        self.init_phase_ui()

        self.training_button = QPushButton("Start Training")
        self.training_button.clicked.connect(self.on_toggle_training)
        self.main_layout.addWidget(self.training_button)

        self.prime_button = QPushButton("Start Priming Feeding Tube")
        self.prime_button.clicked.connect(self.on_toggle_priming)
        self.main_layout.addWidget(self.prime_button)

        self.serial_monitor = QTextEdit()
        self.serial_monitor.setReadOnly(True)
        self.main_layout.addWidget(self.serial_monitor)

        self.rodent_id = None
        self.csv_file = None
        self.pi = None
        self.peripherals = None
        self.trainer = None
        self.board_map = None

        self.init_hardware()

    def init_mouse_info_ui(self):
        mouse_info_group = QGroupBox("Rodent Information")
        mouse_info_layout = QVBoxLayout()

        mouse_info_group.setStyleSheet(
            "QGroupBox { background-color: #D3D3D3; "
            "border: 2px solid #4A4A4A; border-radius: 10px; padding: 10px; }"
        )

        mouse_input_layout = QHBoxLayout()
        self.mouse_name_input = QLineEdit()
        self.mouse_name_input.setPlaceholderText("Enter Mouse ID here")
        mouse_input_layout.addWidget(self.mouse_name_input)

        self.save_mouse_name_button = QPushButton("Save")
        self.save_mouse_name_button.setStyleSheet(
            "background-color: #ffcccb; font-weight: bold; border-radius: 5px;"
        )
        self.save_mouse_name_button.clicked.connect(self.save_mouse_name)
        mouse_input_layout.addWidget(self.save_mouse_name_button)

        mouse_info_layout.addLayout(mouse_input_layout)

        self.mouse_name_label = QLabel("Current Mouse Name: No Mouse Name Set")
        mouse_info_layout.addWidget(self.mouse_name_label)

        mouse_info_group.setLayout(mouse_info_layout)
        self.main_layout.addWidget(mouse_info_group)

    def init_phase_ui(self):
        phase_layout = QHBoxLayout()

        phase_label = QLabel("Select Phase:")
        self.phase_combo = QComboBox()
        self.phase_combo.addItems(["Habituation", "Initial Touch", "Phase 3", "Phase 4"])
        phase_layout.addWidget(phase_label)
        phase_layout.addWidget(self.phase_combo)

        self.load_csv_btn = QPushButton("Load CSV")
        self.load_csv_btn.clicked.connect(self.on_load_csv)
        phase_layout.addWidget(self.load_csv_btn)

        self.main_layout.addLayout(phase_layout)

    def init_hardware(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            self.serial_monitor.append("Failed to connect to pigpio!")
            return

        Reward_LED_PIN = 13
        Reward_PIN = 19
        BeamBreak_PIN = 26

        self.peripherals = {
            'reward_led': LED(self.pi, Reward_LED_PIN),
            'reward':     Reward(self.pi, Reward_PIN),
            'beam_break': BeamBreak(self.pi, BeamBreak_PIN),
        }

        self.board_map = {"M0_0": "/dev/ttyACM0", "M0_1": "/dev/ttyACM1"}

        self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, self.board_map)

    def save_mouse_name(self):
        name = self.mouse_name_input.text().strip()
        if name:
            self.rodent_id = name
            self.mouse_name_label.setText(f"Current Rodent Name: {name}")
            self.serial_monitor.append(f"Rodent ID set to: {name}")
            self.mouse_name_input.clear()
        else:
            self.serial_monitor.append("No rodent name entered.")

    def on_discover(self):
        boards = rpi_m0_comm.discover_m0_boards()
        if boards:
            self.serial_monitor.append("Discovered boards:")
            for bid, dev in boards.items():
                self.serial_monitor.append(f" - {bid} => {dev}")

            self.board_map = boards
            self.trainer = Main.MultiPhaseTraining(self.pi, self.peripherals, boards)
        else:
            self.serial_monitor.append("No M0 boards found.")

    def on_load_csv(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if fname:
            self.csv_file = fname
            self.serial_monitor.append(f"CSV loaded: {fname}")

    def on_toggle_training(self):
        if not self.trainer:
            self.serial_monitor.append("No trainer object available.")
            return
        if not self.csv_file:
            self.serial_monitor.append("No CSV loaded; cannot start training.")
            return

        if not self.is_training:
            self.is_training = True
            self.training_button.setText("Stop Training")

            phase_sel = self.phase_combo.currentText()
            self.serial_monitor.append(f"Starting phase: {phase_sel} with rodent={self.rodent_id}")
            if phase_sel == "Habituation":
                self.trainer.phase_1()  
            elif phase_sel == "Initial Touch":
                self.trainer.initial_touch_phase(self.csv_file)
            elif phase_sel == "Phase 3":
                self.trainer.phase3(self.csv_file)
            elif phase_sel == "Phase 4":
                self.trainer.phase4(self.csv_file)


            self.is_training = False
            self.training_button.setText("Start Training")
        else:
            self.serial_monitor.append("Stopping training...")
            self.trainer.stop_session()
            self.is_training = False
            self.training_button.setText("Start Training")

    def on_toggle_priming(self):
        if not self.trainer:
            self.serial_monitor.append("Error ni priming.")
            return

        if not self.is_priming:
            self.is_priming = True
            self.prime_button.setText("Stop Priming Feeding Tube")
            self.serial_monitor.append("Starting to prime feeding tube for 3s.")

            self.trainer.prime_feeding_tube(3.0)
            self.is_priming = False
            self.prime_button.setText("Start Priming Feeding Tube")
        else:
            self.serial_monitor.append("Stop priming (if it was async).")

            self.is_priming = False
            self.prime_button.setText("Start Priming Feeding Tube")

    def closeEvent(self, event):
        if self.pi and self.pi.connected:
            self.pi.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MultiTrialGUI()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
