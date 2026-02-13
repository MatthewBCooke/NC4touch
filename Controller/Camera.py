import os
import signal
import subprocess
from helpers import get_ip_address

import logging
logger = logging.getLogger(f"session_logger.{__name__}")

#TODO: Set camera parameter using https://community.octoprint.org/t/disable-autofocus-on-usb-webcam-config-using-v4l2-ctl-on-linux/30393
#TODO: Test ustreamer with options given in https://github.com/pikvm/ustreamer

class Camera:
    def __init__(self, device="/dev/video0", stream_port=8080):
        self.device = device

        self.network_stream = None
        self.stream_port = stream_port
        self.video_recorder = None

        # Kill any existing ustreamer or ffmpeg processes
        self.kill_ustreamer()
        self.kill_ffmpeg()

        # Start the video capture
        self.start_video_stream()
    
    def __del__(self):
        # Release resources
        self.stop_video_stream()
        logger.info("Camera object deleted.")
    
    def reinitialize(self):
        # Reinitialize the camera
        if self.video_recorder:
            self.stop_recording()
        if self.network_stream:
            self.stop_video_stream()
            self.kill_ustreamer()
            self.kill_ffmpeg()
            # Wait for a short time to ensure processes are killed
            self.start_video_stream()

        logger.info("Camera reinitialized.")
    
    def kill_ustreamer(self):
        # Kill all ustreamer processes
        try:
            subprocess.call(['pkill', '-f', 'ustreamer'])
            logger.debug("Killed all ustreamer processes.")
        except Exception as e:
            logger.error(f"Error killing ustreamer processes: {e}")
    
    def kill_ffmpeg(self):
        # Kill all ffmpeg processes
        try:
            subprocess.call(['pkill', '-f', 'ffmpeg'])
            logger.debug("Killed all ffmpeg processes.")
        except Exception as e:
            logger.error(f"Error killing ffmpeg processes: {e}")
    
    def start_video_stream(self):
        local_ip = get_ip_address()
        cmd = f"ustreamer --device={self.device} --host={local_ip} --port={self.stream_port} --sink=demo::ustreamer::sink --sink-mode=660 --sink-rm"
        logger.debug(f"Starting ustreamer with command: {cmd}")
        
        # Start the ustreamer process in the background
        self.network_stream = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        
        if self.network_stream:
            logger.info(f"Network stream started on {local_ip}:{self.stream_port}")
        else:
            logger.error("Failed to start network stream.")
    
    def stop_video_stream(self):
        self.stop_recording()
        if self.network_stream:
            # self.network_stream.kill()
            os.killpg(os.getpgid(self.network_stream.pid), signal.SIGTERM)
            self.network_stream = None
            logger.info("Network stream terminated.")
        else:
            logger.warning("No network stream to terminate.")
    
    def start_recording(self, output_file="/mnt/shared/output.mp4"):
        if not self.video_recorder:
            cmd = f"ustreamer-dump --sink=demo::ustreamer::sink --output - | ffmpeg -use_wallclock_as_timestamps 1 -i pipe: -c:v libx264 {output_file}"
            logger.debug(f"Starting recording with command: {cmd}")
            # Start the video recorder
            self.video_recorder = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
            logger.info(f"Recording started: {output_file}")
        else:
            logger.warning("Recording is already in progress.")
    
    def stop_recording(self):
        if self.video_recorder:
            # Stop the video recorder
            os.killpg(os.getpgid(self.video_recorder.pid), signal.SIGTERM)
            self.video_recorder = None
            logger.info("Recording stopped.")
        else:
            logger.warning("No recording in progress.")

if __name__ == "__main__":
    camera = Camera()

    while True:
        pass
