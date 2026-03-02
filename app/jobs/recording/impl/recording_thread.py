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
        self._next_merge_segment = 0
        # Skip segments that were already merged (file exists as final but segments don't)
        for i in range(existing):
            segment = f"{base_name}_{i:03d}{extension}"
            if not os.path.exists(segment):
                self._next_merge_segment = i + 1
            else:
                break

    def run(self):
        self.running = True

        # Start progressive merge daemon thread
        merge_thread = threading.Thread(target=self._progressive_merge_loop, daemon=True)
        merge_thread.start()

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
            self._merge_remaining_segments()
            self.merge_completed = True

            if self.on_completion_callback:
                try:
                    self.on_completion_callback(self.recording)
                except Exception as e:
                    print(f"Error calling recording completion callback: {e}")

    def _progressive_merge_loop(self):
        """Daemon thread that merges segments into the final file as they complete."""
        while self.running:
            try:
                base_name = os.path.splitext(self.file_path)[0]
                extension = os.path.splitext(self.file_path)[1] or '.mkv'

                # A segment is complete when the next segment exists
                current_segment = f"{base_name}_{self._next_merge_segment:03d}{extension}"
                next_segment = f"{base_name}_{self._next_merge_segment + 1:03d}{extension}"

                if os.path.exists(current_segment) and os.path.exists(next_segment):
                    self._merge_single_segment(current_segment)
            except Exception as e:
                print(f"Error in progressive merge loop: {e}")

            time.sleep(2)

    def _merge_single_segment(self, segment_path):
        """Merge a single segment into the final file."""
        try:
            if not os.path.exists(self.file_path):
                # First segment: just rename it
                os.rename(segment_path, self.file_path)
                print(f"Progressive merge: renamed first segment to {self.file_path}")
            else:
                # Concat final file + segment → temp, then rename
                temp_path = self.file_path + ".tmp.mkv"
                concat_list = os.path.join(
                    os.path.dirname(self.file_path),
                    f".concat_{os.getpid()}_{time.time()}.txt"
                )

                with open(concat_list, 'w') as f:
                    f.write(f"file '{os.path.abspath(self.file_path)}'\n")
                    f.write(f"file '{os.path.abspath(segment_path)}'\n")

                cmd = [
                    "ffmpeg", "-y",
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
                    try:
                        os.remove(segment_path)
                    except Exception as e:
                        print(f"Error removing merged segment {segment_path}: {e}")
                    print(f"Progressive merge: appended segment {os.path.basename(segment_path)}")
                else:
                    print(f"Progressive merge failed for {segment_path}: {result.stderr.decode()}")
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                    return

            self._next_merge_segment += 1

        except Exception as e:
            print(f"Error in _merge_single_segment: {e}")

    def _run_ffmpeg(self):
        try:
            input_url = f"rtsp://{self.camera.username}:{self.camera.password}@{self.camera.ip}:{self.camera.port}/{self.camera.path}"

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
                "-analyzeduration", "1M",  # Reduced for faster startup on reconnect
                "-probesize", "1M",  # Reduced for faster startup on reconnect
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

            # Use a temp file for stderr to avoid pipe buffer blocking FFmpeg
            stderr_path = os.path.join(
                os.path.dirname(self.file_path),
                f".ffmpeg_stderr_{os.getpid()}_{self.recording.camera_ip}.log"
            )
            stderr_file = open(stderr_path, 'w')

            with self.lock:
                self.proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )

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

            # Update segment counter by scanning what FFmpeg created
            # Start from _next_merge_segment since earlier segments may have been merged and deleted
            for i in range(self._next_merge_segment, self._next_merge_segment + 1000):
                segment = f"{base_name}_{i:03d}{extension}"
                if os.path.exists(segment):
                    self._segment_counter = i + 1
                else:
                    break

            return ffmpeg_exited_ok

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

    def _merge_remaining_segments(self):
        """Merge any segments the progressive merge thread didn't process yet."""
        try:
            base_name = os.path.splitext(self.file_path)[0]
            extension = os.path.splitext(self.file_path)[1] or '.mkv'

            remaining = []
            for i in range(self._next_merge_segment, self._segment_counter + 10):
                segment = f"{base_name}_{i:03d}{extension}"
                if os.path.exists(segment):
                    remaining.append(segment)
                elif i >= self._segment_counter:
                    break

            if not remaining:
                if not os.path.exists(self.file_path):
                    print(f"No segments found for {self.file_path}")
                return

            print(f"Merging {len(remaining)} remaining segments for {self.file_path}")

            for segment in remaining:
                self._merge_single_segment(segment)

        except Exception as e:
            print(f"Error merging remaining segments for {self.file_path}: {e}")

    def stop(self):
        self.running = False
        self._stop_ffmpeg()
