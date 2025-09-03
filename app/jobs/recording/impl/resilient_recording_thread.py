import os
import threading
import subprocess
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.models.camera import Camera
from app.models.recording import Recording

logger = logging.getLogger(__name__)


class ResilientRecordingThread(threading.Thread):
    def __init__(self, camera: Camera, recording: Recording, on_complete_callback=None):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.on_complete_callback = on_complete_callback
        self.file_path = os.path.join(recording.path, recording.name)
        self.running = None
        self.start_time = datetime.now()
        self.target_duration = 3600 if camera.always_recording else 120
        self.current_proc = None
        self.ffmpeg_segments = []
        self.segment_index = 0
        self.last_successful_connection = datetime.now()

    def run(self):
        self.running = True
        temp_dir = f"/tmp/recording_{self.recording.id}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            while self.running and self._should_continue_recording():
                if self._try_record_segment(temp_dir):
                    self.last_successful_connection = datetime.now()
                    time.sleep(0.1)
                else:
                    if not self._create_black_frames_segment(temp_dir):
                        break
                    time.sleep(2)

            if self.running:
                self._finalize_recording(temp_dir)

        except Exception as e:
            logger.error(f"Error in recording thread for {self.camera.ip}: {e}")
        finally:
            self._cleanup(temp_dir)
            self.running = None
            if self.on_complete_callback:
                self.on_complete_callback(self.recording)

    def _should_continue_recording(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed < self.target_duration

    def _try_record_segment(self, temp_dir):
        try:
            if not self.camera.is_reachable():
                return False

            segment_file = os.path.join(temp_dir, f"segment_{self.segment_index:04d}.mkv")
            input_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

            remaining_time = max(1, self.target_duration - (datetime.now() - self.start_time).total_seconds())
            segment_duration = min(30, remaining_time)

            cmd = [
                "ffmpeg",
                "-y",
                "-rtsp_transport", "tcp",
                "-i", input_url,
                "-t", str(segment_duration),
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "matroska",
                "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts",
                "-loglevel", "error",
                segment_file
            ]

            self.current_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            start_wait = datetime.now()
            while self.running:
                return_code = self.current_proc.poll()
                if return_code is not None:
                    if return_code == 0 and os.path.exists(segment_file) and os.path.getsize(segment_file) > 0:
                        self.ffmpeg_segments.append(segment_file)
                        self.segment_index += 1
                        return True
                    else:
                        if os.path.exists(segment_file):
                            os.remove(segment_file)
                        return False

                if (datetime.now() - start_wait).total_seconds() > segment_duration + 5:
                    self.current_proc.terminate()
                    self.current_proc.wait(timeout=2)
                    if os.path.exists(segment_file):
                        os.remove(segment_file)
                    return False

                if not self.running:
                    self.current_proc.terminate()
                    self.current_proc.wait(timeout=2)
                    if os.path.exists(segment_file):
                        os.remove(segment_file)
                    return False

                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error recording segment for {self.camera.ip}: {e}")
            return False

    def _create_black_frames_segment(self, temp_dir):
        try:
            if not self._should_continue_recording():
                return False

            segment_file = os.path.join(temp_dir, f"black_{self.segment_index:04d}.mkv")
            duration = min(5, self.target_duration - (datetime.now() - self.start_time).total_seconds())

            if duration <= 0:
                return False

            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s=1920x1080:r=15:d={duration}",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:d={duration}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "51",
                "-c:a", "aac",
                "-b:a", "32k",
                "-f", "matroska",
                "-loglevel", "error",
                segment_file
            ]

            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0 and os.path.exists(segment_file):
                self.ffmpeg_segments.append(segment_file)
                self.segment_index += 1
                logger.info(f"Created black frames segment for {self.camera.ip}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error creating black frames for {self.camera.ip}: {e}")
            return False

    def _finalize_recording(self, temp_dir):
        try:
            if not self.ffmpeg_segments:
                logger.warning(f"No segments to finalize for {self.camera.ip}")
                return

            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for segment in self.ffmpeg_segments:
                    f.write(f"file '{segment}'\n")

            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-f", "matroska",
                "-loglevel", "error",
                self.file_path
            ]

            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                logger.error(f"Failed to concatenate segments for {self.camera.ip}: {result.stderr.decode()}")
            else:
                logger.info(f"Successfully finalized recording for {self.camera.ip}")

        except Exception as e:
            logger.error(f"Error finalizing recording for {self.camera.ip}: {e}")

    def _cleanup(self, temp_dir):
        try:
            for segment in self.ffmpeg_segments:
                if os.path.exists(segment):
                    os.remove(segment)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

    def stop(self):
        if self.running is not None:
            self.running = False
            if self.current_proc and self.current_proc.poll() is None:
                self.current_proc.terminate()
                try:
                    self.current_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.current_proc.kill()
            while self.running is not None:
                time.sleep(0.1)