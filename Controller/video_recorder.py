#!/usr/bin/env python3
import cv2
import subprocess
import threading
import os
import time

def merge_audio_video(video_path, audio_path):
    output_file_path = video_path.replace('.avi', '_final.mp4')
    ffmpeg_command = [
        'ffmpeg', '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        output_file_path
    ]
    try:
        subprocess.run(ffmpeg_command, check=True)
        print(f"Video and audio combined into {output_file_path}")
    except Exception as e:
        print(f"Failed to combine video and audio: {e}")

class VideoRecorder:
    def __init__(self, video_capture, audio_device='hw:3,0'):
        """
        video_capture: an already-opened OpenCV capture object.
        audio_device: the ALSA device string for audio capture.
        """
        self.video_capture = video_capture
        self.audio_device = audio_device
        self.livestream_enabled = False
        # For livestream mode, we use one unified FFmpeg process with the tee muxer.
        self.ffmpeg_process = None  
        # For local-only mode, we use cv2.VideoWriter and a separate audio process.
        self.video_writer = None
        self.recording_process = None  # For local-only audio capture.
        self.video_file_path = ""
    
    def start_recording(self, filepath, livestream=False, stream_url=""):
        """
        Starts recording.
          filepath: local file path to save the recording.
          livestream: if True, enables dual-output mode (local file + YouTube livestream via RTMP).
          stream_url: when livestreaming, the RTMP URL (e.g., "rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY").
        Returns True if successful, False otherwise.
        """
        self.livestream_enabled = livestream
        if livestream:
            # For livestream mode both outputs must be identical.
            # YouTube requires FLV with H.264 and AAC audio, so force a .flv extension.
            if not filepath:
                return False
            if not filepath.endswith(".flv"):
                filepath = os.path.splitext(filepath)[0] + ".flv"
            self.video_file_path = filepath

            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 20  # fallback

            # Build the unified FFmpeg command.
            # Audio is captured from ALSA (using self.audio_device),
            # video is read as raw video (bgr24) from stdin.
            # The video stream is split into two identical branches using the split filter.
            # Then the same encoded stream (H.264 with AAC audio) is sent to both outputs:
            #  - One branch goes to the RTMP URL (YouTube Live).
            #  - The other branch saves to the local file.
            ffmpeg_command = [
                'ffmpeg', '-y',
                # Audio input:
                '-f', 'alsa', '-i', self.audio_device,
                # Video input from stdin:
                '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                '-s', f"{width}x{height}",
                '-r', str(int(fps)), '-i', '-',
                # Split the video into two copies:
                '-filter_complex', "[1:v]split=2[v1][v2]",
                # Map audio (from input 0) and video branch [v1]:
                '-map', "0:a", '-map', "[v1]",
                '-c:v', 'h264_v4l2m2m', '-b:v', '3000k',
                '-c:a', 'aac',
                # Use tee muxer to output identically to both destinations:
                '-f', 'tee',
                f"[f=flv]{stream_url}|[f=flv]{filepath}"
            ]
            try:
                self.ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE,
                                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"Started livestreaming:\nRTMP: {stream_url}\nLocal file: {filepath}")
                return True
            except Exception as e:
                print(f"Failed to start FFmpeg process for livestreaming: {e}")
                return False
        else:
            # Local-only mode: use cv2.VideoWriter and separate audio process.
            if not filepath:
                return False
            if not filepath.endswith(".avi"):
                filepath += ".avi"
            self.video_file_path = filepath

            frame_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (frame_width, frame_height))
            self.livestream_enabled = False
            print(f"Started local recording using VideoWriter, saving to {filepath}")

            # Start separate audio capture process:
            audio_file_path = filepath.replace('.avi', '.wav')
            local_audio_cmd = [
                'ffmpeg',
                '-f', 'alsa', '-i', self.audio_device,
                audio_file_path
            ]
            try:
                self.recording_process = subprocess.Popen(local_audio_cmd,
                                                            stdout=subprocess.PIPE,
                                                            stderr=subprocess.PIPE)
                print("Started separate audio recording process for local-only mode.")
            except Exception as e:
                self.recording_process = None
                print(f"Failed to start audio recording for local-only mode: {e}")
            return True

    def update_recording(self, frame):
        """
        Writes the given frame (a NumPy array) to the active FFmpeg process or VideoWriter.
        """
        if self.livestream_enabled:
            if self.ffmpeg_process and self.ffmpeg_process.stdin:
                try:
                    self.ffmpeg_process.stdin.write(frame.tobytes())
                except Exception as e:
                    print(f"Error writing frame to FFmpeg (livestream mode): {e}")
        else:
            if self.video_writer is not None:
                self.video_writer.write(frame)

    def stop_recording(self):
        """
        Stops recording.
        In livestream mode, terminates the unified FFmpeg process.
        In local-only mode, releases the VideoWriter and triggers audio merging.
        """
        if self.livestream_enabled:
            if self.ffmpeg_process:
                try:
                    self.ffmpeg_process.stdin.close()
                    self.ffmpeg_process.wait(timeout=10)
                    print("Livestream FFmpeg process terminated.")
                except Exception as e:
                    print(f"Error terminating livestream FFmpeg process: {e}")
                    try:
                        self.ffmpeg_process.kill()
                    except Exception as kill_e:
                        print(f"Error force-killing livestream FFmpeg process: {kill_e}")
                finally:
                    self.ffmpeg_process = None
        else:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
            print("Stopped local recording using VideoWriter.")
            if self.recording_process:
                threading.Thread(target=self.terminate_ffmpeg_process, daemon=True).start()
            audio_file_path = self.video_file_path.replace('.avi', '.wav')
            if os.path.exists(audio_file_path):
                threading.Thread(target=merge_audio_video, args=(self.video_file_path, audio_file_path), daemon=True).start()
            else:
                print("No audio file found; skipping merge.")

    def terminate_ffmpeg_process(self):
        try:
            self.recording_process.terminate()
            stdout, stderr = self.recording_process.communicate(timeout=5)
            print(f"FFmpeg audio process stdout: {stdout.decode(errors='ignore')}")
            print(f"FFmpeg audio process stderr: {stderr.decode(errors='ignore')}")
        except Exception as e:
            print(f"Error terminating FFmpeg audio process: {e}")
        finally:
            self.recording_process = None
