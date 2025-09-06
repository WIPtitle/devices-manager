import os
import threading
import subprocess
import time
import signal

from app.models.camera import Camera
from app.models.recording import Recording


class RecordingThread(threading.Thread):
    def __init__(self, camera: 'Camera', recording: 'Recording', segment_duration: int, on_completion_callback):
        super().__init__()
        self.camera = camera
        self.recording = recording
        self.segment_duration = segment_duration
        self.on_completion_callback = on_completion_callback
        self.file_path = os.path.join(recording.path, recording.name)
        self.running = False
        self.proc = None
        self.retry_delay = 1
        self.max_retry_delay = 30
        self.lock = threading.Lock()
        self.merge_completed = False

    def run(self):
        self.running = True

        try:
            while self.running:
                try:
                    if not self._run_ffmpeg():
                        if self.running:
                            time.sleep(min(self.retry_delay, self.max_retry_delay))
                            self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
                        continue

                    self.retry_delay = 1

                except Exception as e:
                    print(f"Error in recording thread: {e}")
                    if self.running:
                        time.sleep(min(self.retry_delay, self.max_retry_delay))
                        self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
        finally:
            self._merge_segments()
            self.merge_completed = True

            if self.on_completion_callback:
                try:
                    self.on_completion_callback(self.recording)
                except Exception as e:
                    print(f"Error calling recording completion callback: {e}")

    def _run_ffmpeg(self):
        try:
            input_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

            base_name = os.path.splitext(self.file_path)[0]
            extension = os.path.splitext(self.file_path)[1] or '.mkv'
            segment_path = f"{base_name}_%03d{extension}"

            existing_segments = 0
            for i in range(100):
                segment = f"{base_name}_{i:03d}{extension}"
                if os.path.exists(segment):
                    existing_segments += 1
                else:
                    break

            cmd = [
                "ffmpeg",
                "-y",
                "-use_wallclock_as_timestamps", "1",
                "-rtsp_transport", "tcp",
                "-i", input_url,
                "-fflags", "+genpts+igndts+ignidx+discardcorrupt",
                "-analyzeduration", "10M",
                "-probesize", "10M",
                "-max_delay", "0",
                "-reorder_queue_size", "0",
                "-c:v", "copy",
                "-c:a", "copy",
                "-vsync", "cfr",
                "-f", "segment",
                "-segment_time", str(self.segment_duration),
                "-segment_format", "matroska",
                "-segment_time_delta", "0.1",
                "-segment_atclocktime", "1",
                "-segment_clocktime_offset", "0",
                "-segment_clocktime_wrap_duration", "86400",
                "-reset_timestamps", "1",
                "-break_non_keyframes", "1",
                "-strftime", "0",
                "-segment_start_number", str(existing_segments),
                "-avoid_negative_ts", "make_zero",
                "-loglevel", "warning",
                segment_path
            ]

            with self.lock:
                self.proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )

            while self.running:
                return_code = self.proc.poll()

                if return_code is not None:
                    with self.lock:
                        self.proc = None
                    return False

                time.sleep(0.5)

            self._stop_ffmpeg()
            return False

        except Exception as e:
            print(f"FFmpeg error: {e}")
            return False

    def _stop_ffmpeg(self):
        with self.lock:
            if self.proc:
                try:
                    if os.name != 'nt':
                        self.proc.send_signal(signal.SIGINT)
                        try:
                            self.proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                            try:
                                self.proc.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                                self.proc.wait()
                    else:
                        self.proc.terminate()
                        try:
                            self.proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.proc.kill()
                            self.proc.wait()
                except Exception as e:
                    print(f"Error stopping ffmpeg: {e}")
                finally:
                    self.proc = None

    def _merge_segments(self):
        try:
            base_name = os.path.splitext(self.file_path)[0]
            extension = os.path.splitext(self.file_path)[1] or '.mkv'
            segments = []

            max_segments = 100

            for i in range(max_segments):
                segment = f"{base_name}_{i:03d}{extension}"
                if os.path.exists(segment):
                    segments.append(segment)
                else:
                    break

            if not segments:
                print(f"No segments found for {self.file_path}")
                return

            if len(segments) == 1:
                os.rename(segments[0], self.file_path)
                print(f"Renamed single segment to {self.file_path}")
                return

            concat_list = os.path.join(os.path.dirname(self.file_path), f".concat_{os.getpid()}_{time.time()}.txt")
            with open(concat_list, 'w') as f:
                for segment in segments:
                    f.write(f"file '{os.path.abspath(segment)}'\n")

            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list,
                "-c", "copy",
                "-loglevel", "error",
                self.file_path
            ]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode == 0:
                print(f"Successfully merged {len(segments)} segments into {self.file_path}")
                for segment in segments:
                    try:
                        os.remove(segment)
                    except Exception as e:
                        print(f"Error removing segment {segment}: {e}")
            else:
                print(f"Error merging segments for {self.file_path}: {result.stderr.decode()}")

            try:
                os.remove(concat_list)
            except:
                pass

        except Exception as e:
            print(f"Error merging segments for {self.file_path}: {e}")

    def stop(self):
        self.running = False
        self._stop_ffmpeg()