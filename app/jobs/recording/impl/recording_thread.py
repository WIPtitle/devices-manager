import collections
import os
import threading
import subprocess
import time
import signal

import numpy as np

from app.models.camera import Camera
from app.models.recording import Recording


class FrameBuffer:
    """Thread-safe single-frame buffer with sequence counter for change detection."""
    def __init__(self):
        self._buffer = collections.deque(maxlen=1)
        self._seq = 0

    def put(self, frame):
        self._buffer.append(frame)
        self._seq += 1

    @property
    def seq(self):
        return self._seq

    def get_latest(self):
        """Returns the latest frame, or None if empty."""
        try:
            return self._buffer[-1]
        except IndexError:
            return None


class RecordingThread(threading.Thread):
    DETECTION_FPS = 1
    DETECTION_WIDTH = 640
    DETECTION_HEIGHT = 360

    def __init__(self, camera: 'Camera', recording: 'Recording', segment_duration: int, on_completion_callback,
                 frame_buffer: 'FrameBuffer | None' = None):
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

        # Detection frame buffer (shared with MotionDetectionWorker)
        # Always enabled for always_recording cameras so detection can be toggled at runtime
        self.detection_enabled = camera.always_recording
        if frame_buffer is not None and self.detection_enabled:
            self.frame_buffer = frame_buffer
        elif self.detection_enabled:
            self.frame_buffer = FrameBuffer()
        else:
            self.frame_buffer = None

        base_name = os.path.splitext(self.file_path)[0]
        extension = os.path.splitext(self.file_path)[1] or '.mkv'

        # Scan existing segments to initialize counters
        existing = 0
        for i in range(1000):
            segment = f"{base_name}_{i:03d}{extension}"
            if os.path.exists(segment):
                existing = i + 1
            else:
                break

        self._segment_counter = existing

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
            self._merge_all_segments()
            self.merge_completed = True

            if self.on_completion_callback:
                try:
                    self.on_completion_callback(self.recording)
                except Exception as e:
                    print(f"Error calling recording completion callback: {e}")


    def _run_ffmpeg(self):
        try:
            input_url = self.camera.rtsp_url()

            base_name = os.path.splitext(self.file_path)[0]
            extension = os.path.splitext(self.file_path)[1] or '.mkv'
            segment_path = f"{base_name}_%03d{extension}"

            start_number = self._segment_counter

            cmd = [
                "ffmpeg",
                "-y",
                # Input options
                "-rtsp_transport", "udp",  # UDP: WiFi micro-drops cause frame loss instead of killing FFmpeg
                "-timeout", "2000000",  # 2 sec socket I/O timeout (reduced for faster recovery)
                "-thread_queue_size", "1024",  # Buffer for input packets
                "-analyzeduration", "5M",
                "-probesize", "5M",
                "-fflags", "+genpts+discardcorrupt",  # Generate PTS, discard corrupt frames
                "-i", input_url,
                # Output options
                "-c:v", "copy",
                "-c:a", "copy",
                "-map", "0",
                "-f", "segment",
                "-segment_time", str(self.segment_duration),
                "-segment_format", "matroska",
                "-segment_time_delta", "0.5",
                "-reset_timestamps", "1",
                "-segment_start_number", str(start_number),
                "-avoid_negative_ts", "make_zero",
                # MKV options for better resilience
                "-cluster_size_limit", "2M",  # Smaller clusters = more recovery points
                "-cluster_time_limit", "5000",  # Max 5 sec per cluster
                "-loglevel", "warning",
                segment_path
            ]

            # Output 2: detection frames (if enabled)
            if self.detection_enabled:
                cmd.extend([
                    "-vf", f"fps={self.DETECTION_FPS},scale={self.DETECTION_WIDTH}:{self.DETECTION_HEIGHT}",
                    "-an",
                    "-f", "rawvideo",
                    "-pix_fmt", "bgr24",
                    "pipe:1"
                ])

            # Use a temp file for stderr to avoid pipe buffer blocking FFmpeg
            stderr_path = os.path.join(
                os.path.dirname(self.file_path),
                f".ffmpeg_stderr_{os.getpid()}_{self.recording.camera_ip}.log"
            )
            stderr_file = open(stderr_path, 'w')

            stdout_target = subprocess.PIPE if self.detection_enabled else subprocess.DEVNULL

            with self.lock:
                self.proc = subprocess.Popen(
                    cmd,
                    stdout=stdout_target,
                    stderr=stderr_file,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )

            # Start frame reader thread if detection is enabled
            frame_reader_thread = None
            if self.detection_enabled and self.proc and self.proc.stdout:
                frame_reader_thread = threading.Thread(
                    target=self._read_frames,
                    args=(self.proc,),
                    daemon=True
                )
                frame_reader_thread.start()

            ffmpeg_exited_ok = False
            while self.running:
                return_code = self.proc.poll()

                if return_code is not None:
                    with self.lock:
                        self.proc = None
                    ffmpeg_exited_ok = (return_code == 0)
                    stderr_file.close()
                    try:
                        with open(stderr_path, 'r') as f:
                            stderr_output = f.read().strip()
                        if stderr_output:
                            print(f"FFmpeg exited (code={return_code}) for {self.recording.camera_ip}: {stderr_output[-500:]}")
                        else:
                            print(f"FFmpeg exited (code={return_code}) for {self.recording.camera_ip}")
                        os.remove(stderr_path)
                    except:
                        pass
                    break

                time.sleep(0.5)
            else:
                self._stop_ffmpeg()
                stderr_file.close()
                try:
                    with open(stderr_path, 'r') as f:
                        stderr_output = f.read().strip()
                    if stderr_output:
                        print(f"FFmpeg stopped for {self.recording.camera_ip}: {stderr_output[-500:]}")
                    os.remove(stderr_path)
                except:
                    pass

            # Wait for frame reader to finish
            if frame_reader_thread and frame_reader_thread.is_alive():
                frame_reader_thread.join(timeout=5)

            # Update segment counter by scanning what FFmpeg created
            for i in range(self._segment_counter, self._segment_counter + 1000):
                segment = f"{base_name}_{i:03d}{extension}"
                if os.path.exists(segment):
                    self._segment_counter = i + 1
                else:
                    break

            return ffmpeg_exited_ok

        except Exception as e:
            print(f"FFmpeg error: {e}")
            return False

    def _read_frames(self, proc):
        """Read raw BGR24 frames from FFmpeg stdout into the frame buffer."""
        frame_size = self.DETECTION_WIDTH * self.DETECTION_HEIGHT * 3
        while self.running:
            try:
                raw = proc.stdout.read(frame_size)
                if not raw or len(raw) < frame_size:
                    break
                frame = np.frombuffer(raw, dtype=np.uint8).reshape(
                    (self.DETECTION_HEIGHT, self.DETECTION_WIDTH, 3)
                )
                self.frame_buffer.put(frame)
            except Exception:
                break

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

    def _merge_all_segments(self):
        """Merge all segments into the final file with a single concat operation."""
        try:
            base_name = os.path.splitext(self.file_path)[0]
            extension = os.path.splitext(self.file_path)[1] or '.mkv'

            segments = []
            for i in range(self._segment_counter + 10):
                segment = f"{base_name}_{i:03d}{extension}"
                if os.path.exists(segment):
                    segments.append(segment)
                elif i >= self._segment_counter:
                    break

            if not segments:
                if not os.path.exists(self.file_path):
                    print(f"No segments found for {self.file_path}")
                return

            if len(segments) == 1:
                os.rename(segments[0], self.file_path)
                print(f"Merged 1 segment for {self.file_path}")
                return

            print(f"Merging {len(segments)} segments for {self.file_path}")

            concat_list = os.path.join(
                os.path.dirname(self.file_path),
                f".concat_{os.getpid()}_{time.time()}.txt"
            )
            with open(concat_list, 'w') as f:
                for segment in segments:
                    f.write(f"file '{os.path.abspath(segment)}'\n")

            temp_path = self.file_path + ".tmp.mkv"
            cmd = [
                "ffmpeg", "-y",
                "-fflags", "+genpts",
                "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-c", "copy",
                "-loglevel", "error",
                temp_path
            ]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                os.remove(concat_list)
            except:
                pass

            if result.returncode == 0:
                os.replace(temp_path, self.file_path)
                for segment in segments:
                    try:
                        os.remove(segment)
                    except:
                        pass
                print(f"Merged {len(segments)} segments into {self.file_path}")
            else:
                print(f"Merge failed for {self.file_path}: {result.stderr.decode()}")
                try:
                    os.remove(temp_path)
                except:
                    pass

        except Exception as e:
            print(f"Error merging segments for {self.file_path}: {e}")

    def stop(self):
        self.running = False
        self._stop_ffmpeg()
