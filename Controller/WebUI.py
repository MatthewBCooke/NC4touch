# Create a WebUI using NiceUI that replicates the functionality of TUI
from nicegui import ui, app
from datetime import datetime
import logging

from Trainer import get_trainers
from helpers import get_ip_address
from Session import Session
from file_picker import file_picker

import logging
session_logger = logging.getLogger('session_logger')
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Work on the UI to make it more user friendly and visually appealing

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
    def __init__(self, video_port=8080, ui_port=8081):
        # Initialize session and chamber
        logger.info("Initializing WebUI...")
        self.session = Session()

        self.ip = get_ip_address()
        self.video_port = video_port
        self.ui_port = ui_port

        # Initialize UI
        self.init_ui()

    def init_ui(self):
        ui.label('Chamber Control Panel').style('font-size: 24px; font-weight: bold; text-align: center; margin-top: 20px;')
        with ui.row().style('justify-content: left; margin-top: 20px;'):
            with ui.column().style('width: 400px; margin: auto; padding: 20px;'):
                with ui.row():
                    ui.label('Chamber Name:').style('width: 200px;')
                    self.chamber_name_input = ui.input(self.session.config["chamber_name"],
                                                       on_change = lambda e:self.session.set_chamber_name(e.value)).style('width: 200px;')

                with ui.row():
                    ui.label('Rodent Name:').style('width: 200px;')
                    self.rodent_name_input = ui.input(self.session.config["rodent_name"],
                                                      on_change = lambda e: self.session.set_rodent_name(e.value)).style('width: 200px;')
                
                with ui.row():
                    ui.label('ITI Duration (s):').style('width: 200px;')
                    self.iti_duration_input = ui.input(str(self.session.config["iti_duration"]),
                                                       on_change = lambda e: self.session.set_iti_duration(int(e.value))).style('width: 200px;')

                with ui.row():
                    ui.label('Trainer Sequence Directory:').style('width: 200px;')
                    self.trainer_seq_dir_input = ui.input(self.session.config["trainer_seq_dir"],
                                                          on_change=lambda e: self.session.set_trainer_seq_dir(e.value)).style('width: 200px;')

                with ui.row():
                    ui.label('Trainer Sequence File:').style('width: 200px;')
                    self.trainer_seq_file_button = ui.button("Select File").on_click(self.pick_trainer_seq_file).style('width: 200px;')
                    
                    self.trainer_seq_file_input = ui.input(self.session.config["trainer_seq_file"],
                                                          on_change=lambda e: self.session.set_trainer_seq_file(e.value)).style('width: 200px;')

                with ui.row():
                    self.trainer_seq_file_uploader = ui.upload(auto_upload=True, multiple=False, label="Trainer sequence file",
                                                               on_upload=lambda e: self.session.set_trainer_seq_file(e.name)).classes('max-w-full')

            
            with ui.column().style('width: 400px; margin: auto; padding: 20px;'):
                with ui.row():
                    ui.label('Data Directory:').style('width: 200px;')
                    self.data_dir_input = ui.input(self.session.config["data_dir"],
                                                   on_change=lambda e: self.session.set_data_dir(e.value)).style('width: 200px;')
                
                with ui.row():
                    ui.label('Video Directory:').style('width: 200px;')
                    self.video_dir_input = ui.input(self.session.config["video_dir"],
                                                    on_change=lambda e: self.session.set_video_dir(e.value)).style('width: 200px;')
                
                with ui.row():
                    ui.label('Trainer:').style('width: 200px;')
                    self.trainer_select = ui.select(get_trainers(), value='DoNothingTrainer', on_change=lambda e: self.session.set_trainer_name(e.value)).style('width: 200px;')

                with ui.card():
                    ui.label('M0 Board Control').style('font-size: 18px; font-weight: bold; text-align: center; margin-top: 20px;')
                    with ui.column():
                        # Buttons to control M0 boards
                        self.discover_button = ui.button("Discover").on_click(self.session.chamber.m0_discover)
                        self.reset_button = ui.button("Reset").on_click(self.session.chamber.m0_reset)
                        self.reinitialize_button = ui.button("Re-Initialize").on_click(self.session.chamber.m0_initialize)
                        self.sync_images_button = ui.button("Sync Images").on_click(self.session.chamber.m0_sync_images)
                        self.upload_code_button = ui.button("Upload Code").on_click(self.session.chamber.m0_upload_sketches)
                    with ui.column():
                        # Status labels for M0 boards
                        self.m0_status_labels = []
                        for m0 in self.session.chamber.m0s:
                            label = ui.label(f"{m0.id}: {m0.port}").style('width: 200px;')
                            self.m0_status_labels.append(label)

            with ui.column().style('width: 800px; margin: auto; padding: 20px;'):
                with ui.row():
                    log = ui.log(max_lines=10).classes('w-full')
                    self.log_handler = LogElementHandler(log)
                    formatter = logging.Formatter('[%(asctime)s:%(name)s] %(message)s')
                    self.log_handler.setFormatter(formatter)
                    session_logger.addHandler(self.log_handler)
                    ui.context.client.on_disconnect(lambda: logger.removeHandler(self.log_handler))
                    ui.label('Log Level:').style('width: 200px;')
                    self.log_level_input = ui.select(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], value='DEBUG').style('width: 200px;')
                    self.log_level_input.on('change', lambda e: self.log_handler.setLevel(getattr(logging, e.value)))

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
                
                with ui.row():
                    # Slider to control house LED brightness
                    ui.label('House LED Brightness:').style('width: 200px;')
                    self.house_led_brightness_slider = ui.slider(min=0, max=100, value=self.session.chamber.house_led.brightness,
                                                                on_change=lambda e: self.session.chamber.house_led.set_brightness(e.value)).style('width: 400px;')

        with ui.row().style('justify-content: center; margin-top: 20px;'):
            self.start_training_button = ui.button("Start Training").on_click(self.session.start_training)
            self.stop_training_button = ui.button("Stop Training").on_click(self.session.stop_training)
            self.start_priming_button = ui.button("Start Priming").on_click(self.session.start_priming)
            self.stop_priming_button = ui.button("Stop Priming").on_click(self.session.stop_priming)
    
    async def pick_trainer_seq_file(self) -> None:
        result = await file_picker(directory = self.session.config["trainer_seq_dir"], multiple = False)
        if result is None:
            logger.info("No file selected")
            return
        
        logger.info(f"File selected: {result[0]}")
        self.session.set_trainer_seq_file(result[0])
        self.trainer_seq_file_input.set_value(result[0])

web_ui = WebUI()
ui.run(host=web_ui.ip, port=web_ui.ui_port, title="Chamber Control Panel", show=False)