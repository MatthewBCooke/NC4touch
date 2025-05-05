import os
import subprocess
from helpers import get_ip_address

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

class Camera:
    def __init__(self, camera_device="/dev/video0", stream_port=8080):
        self.camera_device = camera_device

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
        print("Camera object deleted.")
    
    def kill_ustreamer(self):
        # Kill all ustreamer processes
        try:
            subprocess.call(['pkill', '-f', 'ustreamer'])
            print("Killed all ustreamer processes.")
        except Exception as e:
            print(f"Error killing ustreamer processes: {e}")
    
    def kill_ffmpeg(self):
        # Kill all ffmpeg processes
        try:
            subprocess.call(['pkill', '-f', 'ffmpeg'])
            print("Killed all ffmpeg processes.")
        except Exception as e:
            print(f"Error killing ffmpeg processes: {e}")
    
    def start_video_stream(self):
        local_ip = get_ip_address()
        cmd = f"ustreamer --device={self.camera_device} --host={local_ip} --port={self.stream_port} --sink=demo::ustreamer::sink --sink-mode=660 --sink-rm"
        print(f"Starting ustreamer with command: {cmd}")
        
        # Start the ustreamer process in the background
        self.network_stream = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        
        if self.network_stream:
            print(f"Network stream started on {local_ip}:8080")
        else:
            print("Failed to start network stream.")
    
    def stop_video_stream(self):
        self.stop_recording()
        if self.network_stream:
            # self.network_stream.kill()
            os.killpg(os.getpgid(self.network_stream.pid), subprocess.signal.SIGTERM)
            self.network_stream = None
            print("Network stream terminated.")
        else:
            print("No network stream to terminate.")
    
    def start_recording(self, output_file="/mnt/shared/output.mp4"):
        if not self.video_recorder:
            cmd = f"ustreamer-dump --sink=demo::ustreamer::sink --output - | ffmpeg -use_wallclock_as_timestamps 1 -i pipe: -c:v libx264 {output_file}"
            print(f"Starting recording with command: {cmd}")
            # Start the video recorder
            self.video_recorder = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
            print(f"Recording started: {output_file}")
        else:
            print("Already recording.")
    
    def stop_recording(self):
        if self.video_recorder:
            # Stop the video recorder
            os.killpg(os.getpgid(self.video_recorder.pid), subprocess.signal.SIGTERM)
            self.video_recorder = None
            print("Recording stopped.")
        else:
            print("No recording in progress.")

if __name__ == "__main__":
    camera = Camera()

    while True:
        pass
