# Create a WebUI using NiceUI that replicates the functionality of TUI
from nicegui import ui
from datetime import datetime
import logging

from Trainer import get_trainers
from helpers import get_ip_address
from Session import Session

import logging
session_logger = logging.getLogger('session_logger')
logger = logging.getLogger(f"session_logger.{__name__}")

class LogElementHandler(logging.Handler):
    """A logging handler that emits messages to a log element.
        https://nicegui.io/documentation/log    
    """

    def __init__(self, element: ui.log, level: int = logging.NOTSET) -> None:
        self.element = element
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.element.push(msg)
        except Exception:
            self.handleError(record)

class WebUI:
    def __init__(self):
        # Initialize session and chamber
        self.session = Session()

        self.ip = get_ip_address()
        self.video_port = 8080
        self.ui_port = 8081

        # Initialize UI
        self.init_ui()


    def init_ui(self):
        ui.label('Chamber Control Panel').style('font-size: 24px; font-weight: bold; text-align: center; margin-top: 20px;')
        with ui.row().style('justify-content: left; margin-top: 20px;'):
            with ui.column().style('width: 400px; margin: auto; padding: 20px;'):
                with ui.row():
                    ui.label('Rodent Name:').style('width: 200px;')
                    self.rodent_name_input = ui.input(self.session.rodent_name).style('width: 200px;')
                    self.rodent_name_input.on('change', lambda e: self.session.set_rodent_name(e.value))
                
                with ui.row():
                    ui.label('ITI Duration (s):').style('width: 200px;')
                    self.iti_duration_input = ui.input(str(self.session.iti_duration)).style('width: 200px;')
                    self.iti_duration_input.on('change', lambda e: self.session.set_iti_duration(int(e.value)))

                with ui.row():
                    ui.label('Sequence CSV Directory:').style('width: 200px;')
                    self.seq_csv_dir_input = ui.input(self.session.seq_csv_dir).style('width: 200px;')
                    self.seq_csv_dir_input.on('change', lambda e: self.session.set_seq_csv_dir(e.value))

                with ui.row():
                    ui.label('Sequence CSV File:').style('width: 200px;')
                    self.seq_csv_file_input = ui.input(self.session.seq_csv_file).style('width: 200px;')
                    self.seq_csv_dir_input.on('change', lambda e: self.session.set_seq_csv_file(e.value))
            
            with ui.column().style('width: 400px; margin: auto; padding: 20px;'):
                with ui.row():
                    ui.label('Data CSV Directory:').style('width: 200px;')
                    self.data_csv_dir_input = ui.input(self.session.data_csv_dir).style('width: 200px;')
                    self.data_csv_dir_input.on('change', lambda e: self.session.set_data_csv_dir(e.value))

                with ui.row():
                    ui.label('Video Directory:').style('width: 200px;')
                    self.video_dir_input = ui.input(self.session.video_dir).style('width: 200px;')
                    self.video_dir_input.on('change', lambda e: self.session.set_video_dir(e.value))
                
                with ui.row():
                    ui.label('Trainer:').style('width: 200px;')
                    self.trainer_select = ui.select(get_trainers(), value='DoNothingTrainer', on_change = lambda e: self.session.set_trainer_name(e.value)).style('width: 200px;')


            with ui.column().style('width: 800px; margin: auto; padding: 20px;'):
                with ui.row():
                    log = ui.log(max_lines=10).classes('w-full')
                    handler = LogElementHandler(log)
                    formatter = logging.Formatter('[%(asctime)s:%(name)s] %(message)s')
                    handler.setFormatter(formatter)
                    session_logger.addHandler(handler)
                    ui.context.client.on_disconnect(lambda: logger.removeHandler(handler))
                    ui.label('Log Level:').style('width: 200px;')
                    self.log_level_input = ui.select(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], value='DEBUG').style('width: 200px;')
                    self.log_level_input.on('change', lambda e: logger.setLevel(getattr(logging, e.value)))

                with ui.row():
                    # Show video stream from the camera
                    ui.label('Camera Stream:').style('width: 800px;')
                    ui.image(source=f"http://{self.ip}:{self.video_port}/stream").style('width: 640px; height: 480px;')
                
                with ui.row():
                    # Reinitialize the camera
                    self.reinitialize_camera_button = ui.button("Reinitialize").on_click(self.session.chamber.camera.reinitialize)
                    self.reinitialize_camera_button.style('width: 200px; margin-top: 20px;')
                    self.start_video_recording_button = ui.button("Start Video Recording").on_click(self.session.start_video_recording)
                    self.stop_video_recording_button = ui.button("Stop Video Recording").on_click(self.session.stop_video_recording)

        with ui.row().style('justify-content: center; margin-top: 20px;'):
            self.start_training_button = ui.button("Start Training").on_click(self.session.start_training)
            self.stop_training_button = ui.button("Stop Training").on_click(self.session.stop_training)
            self.start_priming_button = ui.button("Start Priming").on_click(self.session.start_priming)
            self.stop_priming_button = ui.button("Stop Priming").on_click(self.session.stop_priming)

if __name__ in {'__main__', '__mp_main__'}:
    web_ui = WebUI()
    ui.run(title='Chamber Control Panel', host=web_ui.ip, port=web_ui.ui_port, show=False)