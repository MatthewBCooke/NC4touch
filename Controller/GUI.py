#!/usr/bin/env python3
import sys
import os
import cv2
import subprocess
import time
from datetime import datetime
import threading

from Camera import Camera

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QGroupBox,
    QLineEdit, QComboBox, QStyleFactory, QMessageBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QImage, QPixmap

# Matplotlib for bar chart
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from Controller.Session import Session

class EmittingStream(QObject):
    """
    A 'file-like' stream that emits a signal whenever text is written.
    This avoids GUI updates from non-GUI threads that can lead to segfaults.
    """
    textWritten = pyqtSignal(str)
    def write(self, text):
        self.textWritten.emit(text)
    def flush(self):
        pass


class MultiTrialGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NC4Touch GUI")
        self.setGeometry(200, 50, 1400, 800)

        # Main layout
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QHBoxLayout(central)
        self.main_layout.setSpacing(25)
        central.setStyleSheet("background-color: #ECECEC;")

        # Two columns
        self.left_column = QVBoxLayout()
        self.left_column.setContentsMargins(15, 15, 15, 15)
        self.left_column.setSpacing(20)
        self.right_column = QVBoxLayout()
        self.right_column.setContentsMargins(15, 15, 15, 15)
        self.right_column.setSpacing(20)
        self.main_layout.addLayout(self.left_column, stretch=1)
        self.main_layout.addLayout(self.right_column, stretch=1)

        # Counters for bar chart
        self.correct_count = 0
        self.incorrect_count = 0
        self.notouch_count = 0
        self.trial_count = 0

        self.session = Session()
        self.config = self.session.config
        self.camera = None
        self.trainer = None
        self.is_recording = False
        self.rodent_names = []

        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.update_session_timer)

        # Initialize GUI components
        self.init_rodent_info_ui()
        self.init_video_ui()
        self.init_graph_ui()

        self.init_discover_button()
        self.init_phase_ui()
        self.init_parameters_ui()  # Parameters UI for ITI
        self.init_session_controls()
        self.init_serial_monitor()

        # Redirect stdout to GUI text monitor
        self.stdout_buffer = ""
        self.emitting_stream = EmittingStream()
        self.emitting_stream.textWritten.connect(self.handle_new_text)
        sys.stdout = self.emitting_stream

        # Disable "Start Training" until a rodent name is set
        self.start_training_btn.setEnabled(False)

        # Start camera capture and create VideoRecorder instance
        self.initialize_video_capture()

    # ---------------- LEFT COLUMN UI ----------------

    def init_rodent_info_ui(self):
        self.rodent_info_group = QGroupBox("Rodent Information")
        self.rodent_info_group.setStyleSheet("""
            QGroupBox {
                background-color: #F9F9F9;
                border: 2px solid #4A4A4A;
                border-radius: 8px;
                margin-top: 10px;
                margin-bottom: 10px;
                padding-top: 25px;
                padding-bottom: 15px;
                padding-left: 15px;
                padding-right: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #333;
                font-weight: bold;
            }
        """)
        self.rodent_info_group.setMaximumHeight(200)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        rodent_input_layout = QHBoxLayout()
        rodent_input_layout.setSpacing(10)

        self.rodent_name_input = QLineEdit()
        self.rodent_name_input.setPlaceholderText("Enter Rodent ID here")
        self.rodent_name_input.setStyleSheet("background-color: #FCF8E3; padding: 4px;")
        rodent_input_layout.addWidget(self.rodent_name_input)

        self.save_rodent_name_button = QPushButton("Save")
        self.save_rodent_name_button.clicked.connect(self.save_rodent_name)
        rodent_input_layout.addWidget(self.save_rodent_name_button)
        layout.addLayout(rodent_input_layout)

        self.rodent_name_label = QLabel("Current Rodent Name: No Rodent Name Set")
        self.rodent_name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        layout.addWidget(self.rodent_name_label)

        self.rodent_name_history_label = QLabel("Trained Rodents: (none yet)")
        self.rodent_name_history_label.setStyleSheet("font-size: 12px; color: #555;")
        layout.addWidget(self.rodent_name_history_label)

        self.rodent_info_group.setLayout(layout)
        self.left_column.addWidget(self.rodent_info_group)

    def init_video_ui(self):
        self.video_group = QGroupBox("Video Recording")
        self.video_group.setStyleSheet("""
            QGroupBox {
                background-color: #F9F9F9;
                border: 2px solid #4A4A4A;
                border-radius: 8px;
                margin-top: 10px;
                margin-bottom: 10px;
                padding-top: 25px;
                padding-bottom: 15px;
                padding-left: 15px;
                padding-right: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #333;
                font-weight: bold;
            }
        """)
        self.video_group.setMinimumHeight(250)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.video_feed_label = QLabel("No Camera Feed")
        self.video_feed_label.setAlignment(Qt.AlignCenter)
        self.video_feed_label.setFixedSize(320, 240)
        self.video_feed_label.setScaledContents(True)
        layout.addWidget(self.video_feed_label)

        self.record_toggle_button = QPushButton("Start Recording")
        self.record_toggle_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_toggle_button)

        self.video_group.setLayout(layout)
        self.left_column.addWidget(self.video_group)

    def init_graph_ui(self):
        self.graph_group = QGroupBox("Real-Time Performance")
        self.graph_group.setStyleSheet("""
            QGroupBox {
                background-color: #F9F9F9;
                border: 2px solid #4A4A4A;
                border-radius: 8px;
                margin-top: 10px;
                margin-bottom: 10px;
                padding-top: 25px;
                padding-bottom: 15px;
                padding-left: 15px;
                padding-right: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #333;
                font-weight: bold;
            }
        """)
        graph_layout = QVBoxLayout()
        graph_layout.setSpacing(10)

        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(20)

        self.trial_count_label = QLabel("Trial Count: 0")
        self.trial_count_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        top_row_layout.addWidget(self.trial_count_label)

        self.session_timer_label = QLabel("Session Time: 00:00")
        self.session_timer_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        top_row_layout.addWidget(self.session_timer_label)

        graph_layout.addLayout(top_row_layout)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        categories = ["correct", "incorrect", "no_touch"]
        counts = [0, 0, 0]
        bar_colors = ["#009E73", "#D55E00", "#0072B2"]
        self.ax.bar(categories, counts, color=bar_colors)
        self.ax.set_ylim([0, 30])
        self.canvas.draw()

        graph_layout.addWidget(self.canvas)
        self.graph_group.setLayout(graph_layout)
        self.left_column.addWidget(self.graph_group)

    # ---------------- RIGHT COLUMN UI ----------------
    def init_discover_button(self):
        self.discover_button = QPushButton("Discover M0 Boards")
        self.discover_button.setStyleSheet("""
            QPushButton {
                background-color: #E69F00;
                color: black;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #FFAE00;
            }
        """)
        self.discover_button.clicked.connect(self.session.discover_m0s)
        self.right_column.addWidget(self.discover_button)

    def init_phase_ui(self):
        phase_layout = QHBoxLayout()
        phase_layout.setSpacing(10)

        phase_label = QLabel("Select Phase:")
        phase_label.setStyleSheet("font-weight: bold;")

        self.phase_combo = QComboBox()
        self.phase_combo.addItems(["Habituation", "Initial Touch", "Must Touch", "Must Initiate", "Punish Incorrect", "Simple Discrimination", "Complex Discrimination"])
        self.phase_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFF7E0;
                font-weight: bold;
                padding: 4px;
            }
        """)

        self.load_csv_btn = QPushButton("Load CSV")
        self.load_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0E442;
                color: black;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #F4E97E;
            }
        """)
        self.load_csv_btn.clicked.connect(self.on_load_seq_csv)

        phase_layout.addWidget(phase_label)
        phase_layout.addWidget(self.phase_combo)
        phase_layout.addWidget(self.load_csv_btn)
        self.right_column.addLayout(phase_layout)

    def init_parameters_ui(self):
        self.param_group = QGroupBox("Parameters")
        self.param_group.setStyleSheet("""
            QGroupBox {
                background-color: #F9F9F9;
                border: 2px solid #4A4A4A;
                border-radius: 8px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #333;
                font-weight: bold;
            }
        """)
        layout = QHBoxLayout()
        iti_label = QLabel("Inter-Trial Interval (s):")
        self.iti_input = QSpinBox()
        self.iti_input.setMinimum(1)
        self.iti_input.setMaximum(300)
        self.iti_input.setValue(10)
        layout.addWidget(iti_label)
        layout.addWidget(self.iti_input)
        self.param_group.setLayout(layout)
        self.right_column.addWidget(self.param_group)

    def init_session_controls(self):
        self.session_group = QGroupBox("Session Controls")
        self.session_group.setStyleSheet("""
            QGroupBox {
                background-color: #F9F9F9;
                border: 2px solid #4A4A4A;
                border-radius: 8px;
                margin-top: 10px;
                margin-bottom: 10px;
                padding-top: 25px;
                padding-bottom: 15px;
                padding-left: 15px;
                padding-right: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #333;
                font-weight: bold;
            }
        """)
        session_layout = QHBoxLayout()
        session_layout.setSpacing(10)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #0072B2;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #1082C2;
            }
        """)
        self.export_csv_btn.clicked.connect(self.on_export_data_csv)
        session_layout.addWidget(self.export_csv_btn)

        self.start_training_btn = QPushButton("Start Training")
        self.start_training_btn.setStyleSheet("""
            QPushButton {
                background-color: #009E73;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #01B583;
            }
        """)
        self.start_training_btn.clicked.connect(self.on_start_training)
        self.start_training_btn.setEnabled(False)
        session_layout.addWidget(self.start_training_btn)

        self.stop_training_btn = QPushButton("Stop Training")
        self.stop_training_btn.setStyleSheet("""
            QPushButton {
                background-color: #D55E00;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #E1721A;
            }
        """)
        self.stop_training_btn.clicked.connect(self.on_stop_training)
        session_layout.addWidget(self.stop_training_btn)

        self.start_priming_btn = QPushButton("Start Priming")
        self.start_priming_btn.setStyleSheet("""
            QPushButton {
                background-color: #90EE90;
                color: black;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #A5F2A5;
            }
        """)
        self.start_priming_btn.clicked.connect(self.on_start_priming)
        session_layout.addWidget(self.start_priming_btn)

        self.stop_priming_btn = QPushButton("Stop Priming")
        self.stop_priming_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFB6C1;
                color: black;
                font-weight: bold;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #FFC6D1;
            }
        """)
        self.stop_priming_btn.clicked.connect(self.on_stop_priming)
        session_layout.addWidget(self.stop_priming_btn)

        self.session_group.setLayout(session_layout)
        self.right_column.addWidget(self.session_group)

    def init_serial_monitor(self):
        self.serial_monitor = QTextEdit()
        self.serial_monitor.setReadOnly(True)
        self.serial_monitor.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #BBBBBB;
                font-family: Consolas, Courier, monospace;
                font-size: 12px;
                padding: 5px;
            }
        """)
        self.right_column.addWidget(self.serial_monitor)


    # ---------------- STDOUT Redirection ----------------
    def handle_new_text(self, text):
        self.stdout_buffer += text
        while "\n" in self.stdout_buffer:
            line, self.stdout_buffer = self.stdout_buffer.split("\n", 1)
            line = line.strip()
            if line:
                self.handle_stdout_line(line)

    def handle_stdout_line(self, line):
        now_str = datetime.now().strftime("%H:%M:%S")
        line_with_ts = f"[{now_str}] {line}"
        self.serial_monitor.append(line_with_ts)
        self.serial_monitor.ensureCursorVisible()

        import re
        match = re.search(r"=== Trial (\d+):", line)
        if match:
            try:
                tnum = int(match.group(1))
                self.trial_count = tnum
                self.trial_count_label.setText(f"Trial Count: {self.trial_count}")
                self.update_graph()
            except ValueError:
                pass

        if "Correct choice" in line:
            self.correct_count += 1
            self.update_graph()
        elif "Incorrect choice" in line:
            self.incorrect_count += 1
            self.update_graph()
        elif "No touch" in line:
            self.notouch_count += 1
            self.update_graph()

    def update_graph(self):
        self.ax.clear()
        categories = ["correct", "incorrect", "no_touch"]
        counts = [self.correct_count, self.incorrect_count, self.notouch_count]
        colors = ["#009E73", "#D55E00", "#0072B2"]

        self.ax.bar(categories, counts, color=colors)
        self.ax.set_ylim([0, 30])
        self.ax.set_title("Real-Time Training Performance", fontsize=14, fontweight='bold')
        self.ax.set_ylabel("Count", fontsize=12)
        self.ax.set_xlabel("Choice Result", fontsize=12)
        self.trial_count_label.setText(f"Trial Count: {self.trial_count}")
        self.canvas.draw()

    def clear_graph(self):
        self.correct_count = 0
        self.incorrect_count = 0
        self.notouch_count = 0
        self.trial_count = 0

        self.ax.clear()
        categories = ["correct", "incorrect", "no_touch"]
        self.ax.bar(categories, [0, 0, 0], color=["#009E73","#D55E00","#0072B2"])
        self.ax.set_ylim([0, 30])
        self.canvas.draw()
        self.trial_count_label.setText("Trial Count: 0")

    # ---------------- VIDEO CAPTURE ----------------
    def initialize_video_capture(self):
        self.session.setup_camera(camera_device="/dev/video0", mode="video_capture")
        self.camera = self.session.camera
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.update_video_feed)
        self.video_timer.start(int(1000 / 30))

    def update_video_feed(self):
        if not self.camera.video_capture or not self.camera.video_capture.isOpened():
            return
        ret, frame = self.camera.video_capture.read()
        if not ret or frame is None:
            return
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_feed_label.setPixmap(QPixmap.fromImage(q_img))
        # Send frame to VideoRecorder for recording (local or livestream mode)
        if self.is_recording and self.camera.video_recorder:
            self.camera.video_recorder.update_recording(frame)

    def toggle_recording(self):
        if self.is_recording:
            self.session.stop_recording()
            self.is_recording = False
            self.record_toggle_button.setText("Start Recording")
        else:
            options = QFileDialog.Options()

            config_recording_dir = self.session.load_from_config("recording_dir")

            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Video", config_recording_dir, "Video Files (*.avi);;Video Files (*.mp4)", options=options
            )
            if not filepath:
                return
            
            self.session.save_to_config("recording_dir", os.path.dirname(filepath))

            if self.session.start_recording(filepath):
                self.is_recording = True
                self.record_toggle_button.setText("Stop Recording")

            # reply = QMessageBox.question(
            #     self,
            #     "Livestream Option",
            #     "Would you like to livestream your recording?",
            #     QMessageBox.Yes | QMessageBox.No
            # )
            # livestream = (reply == QMessageBox.Yes)
            # rtmp_url = ""
            # if livestream:
            #     # Replace YOUR_STREAM_KEY with your actual YouTube stream key.
            #     rtmp_url = "rtmp://x.rtmp.youtube.com/live2/myxg-tayp-8cwx-wecv-ftv9"
            # if self.camera.video_recorder.start_recording(filepath, livestream=livestream, stream_url=rtmp_url):

    
    def on_load_seq_csv(self):
        config_seq_csv_dir = self.session.load_from_config("seq_csv_dir")

        fname, _ = QFileDialog.getOpenFileName(
            self, "Open Sequence CSV", config_seq_csv_dir, "CSV Files (*.csv)"
        )
        if fname:
            self.csv_file = fname
            print(f"CSV loaded: {fname}")

            self.session.save_to_config("seq_csv_dir", os.path.dirname(fname))
            self.session.save_to_config("seq_csv_file", fname)

    def on_export_data_csv(self):
        if not self.trainer:
            print("No trainer object to export from.")
            return
        
        config_data_csv_dir = self.session.load_from_config("data_csv_dir")

        fname, _ = QFileDialog.getSaveFileName(
            self, "Save Data CSV", config_data_csv_dir, "CSV Files (*.csv)"
        )
        if fname:
            self.trainer.rodent_id = self.rodent_name
            self.trainer.export_results_csv(fname)
            print(f"Exported trial data to {fname}")

            self.session.save_to_config("data_csv_dir", os.path.dirname(fname))
        else:
            print("Export canceled.")

    def on_start_training(self):
        self.trainer = self.session.trainer
        if not self.trainer:
            print("No trainer object available.")
            return
        if not self.rodent_name:
            print("Please set rodent name first.")
            return

        phase_sel = self.phase_combo.currentText()
        self.trainer.current_phase = phase_sel
        self.trainer.iti_duration = self.iti_input.value()

        reply = QMessageBox.question(
            self,
            "Confirm Training Phase",
            f"You have selected the '{phase_sel}' training for rodent '{self.rodent_name}'.\n\nPress OK to proceed.",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply == QMessageBox.Cancel:
            print("Training canceled by user.")
            return

        self.start_priming_btn.setEnabled(False)
        self.stop_priming_btn.setEnabled(False)

        self.trainer.trial_data = []
        self.clear_graph()

        if phase_sel != "Habituation" and not self.csv_file:
            print("No CSV loaded; cannot start training for this phase.")
            return

        self.session_start_time = time.time()
        self.session_timer.start(1000)

        print(f"Starting phase: {phase_sel}, rodent={self.rodent_name}")
        if phase_sel == "Habituation":
            self.trainer.Habituation()
        elif phase_sel == "Initial Touch":
            self.trainer.initial_touch_phase(self.csv_file)
        elif phase_sel == "Must Touch":
            self.trainer.must_touch_phase(self.csv_file)
        elif phase_sel == "Must Initiate":
            self.trainer.must_initiate_phase(self.csv_file)
        elif phase_sel == "Punish Incorrect":
            self.trainer.punish_incorrect_phase(self.csv_file)
        elif phase_sel == "Simple Discrimination":
            self.trainer.simple_discrimination_phase(self.csv_file)
        elif phase_sel == "Complex Discrimination":
            self.trainer.complex_discrimination_phase(self.csv_file)
        print("Phase run finished.")

    def on_stop_training(self):
        print("Stopping training now.")
        if self.trainer:
            self.trainer.stop_session()
        self.clear_graph()
        self.session_timer.stop()
        self.session_start_time = None
        self.session_timer_label.setText("Session Time: 00:00")
        self.start_priming_btn.setEnabled(True)
        self.stop_priming_btn.setEnabled(True)

    def on_start_priming(self):
        if not self.trainer or 'reward' not in self.trainer.peripherals:
            print("No trainer or reward object to prime.")
            return
        print("Starting to prime feeding tube.")
        self.trainer.peripherals['reward'].prime_feeding_tube()

    def on_stop_priming(self):
        if not self.trainer or 'reward' not in self.trainer.peripherals:
            print("No trainer or reward object to stop priming.")
            return
        print("Stopping priming.")
        self.trainer.peripherals['reward'].stop_priming()

    def save_rodent_name(self):
        name = self.rodent_name_input.text().strip()
        if name:
            self.rodent_name = name
            self.session.rodent_name = name
            if self.trainer:
                self.trainer.rodent_id = name
            self.rodent_name_label.setText(f"Current Rodent Name: {name}")
            print(f"Rodent ID set to: {name}")
            self.rodent_names.append(name)
            if len(self.rodent_names) == 1:
                self.rodent_name_history_label.setText(f"Trained Rodents:\n - {name}")
            else:
                lines = [f" - {n}" for n in self.rodent_names]
                all_names_str = "\n".join(lines)
                self.rodent_name_history_label.setText(f"Trained Rodents:\n{all_names_str}")
            self.rodent_name_input.clear()
            self.start_training_btn.setEnabled(True)
        else:
            print("No rodent name entered.")

    # ---------------- SESSION TIMER WITH 60-MINUTE CHECK ----------------
    def update_session_timer(self):
        if self.session_start_time is not None:
            elapsed = time.time() - self.session_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.session_timer_label.setText(f"Session Time: {minutes:02d}:{seconds:02d}")

            # Check if 60 minutes (3600 seconds) have passed and ensure the popup shows only once
            if elapsed >= 3600 and not hasattr(self, 'termination_popup_shown'):
                self.termination_popup_shown = True  # Flag so we only show the popup once

                # Create a non-blocking message box
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Session Timeout")
                msg.setText("60 minutes have passed since the start of training.\nWould you like to terminate the training session?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.buttonClicked.connect(self.handle_termination_response)
                msg.show()  # non-blocking

    def handle_termination_response(self, button):
        if button.text() == "&Yes":
            print("User chose to terminate the session after 60 minutes.")
            self.on_stop_training()  # Stop training as if the Stop Training button was pressed
        else:
            print("User chose to continue training.")

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    gui = MultiTrialGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
