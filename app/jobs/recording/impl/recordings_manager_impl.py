import glob
import os
import re
import subprocess
import threading
import time
from threading import Lock, Event

from app.jobs.recording.impl.recording_thread import RecordingThread
from app.jobs.recording.recordings_manager import RecordingsManager
from app.models.disk_usage import DiskUsage
from app.models.recording import Recording, get_recordings_path, get_alarm_recordings_path, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository
from app.utils.delayed_execution import delay_execution


def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        return os.path.basename(file_path)
    return None


class RecordingsManagerImpl(RecordingsManager):
    def __init__(self, camera_repository: CameraRepository, recording_repository: RecordingRepository):
        self.camera_repository = camera_repository
        self.recording_repository = recording_repository
        self.active_recordings = {}
        self.active_threads = {}
        self.lock = Lock()
        self._cleanup_lock = Lock()
        self._scheduler_stop_event = threading.Event()
        self._scheduler_thread = None

        self.alarm_recording_duration = int(os.getenv('ALARM_RECORDING_DURATION_SECONDS', '120'))
        self.always_recording_duration = int(os.getenv('ALWAYS_RECORDING_DURATION_SECONDS', '3600'))
        self.cleanup_interval_seconds = int(os.getenv('CLEANUP_INTERVAL_SECONDS', '3600'))  # Default 1 hour

        self._start_cleanup_scheduler()
        self._recover_incomplete_recordings()

    def is_recording(self, camera_ip: str):
        with self.lock:
            return camera_ip in self.active_recordings

    def start_recording(self, recording: Recording):
        camera = self.camera_repository.find_by_ip(recording.camera_ip)

        with self.lock:
            if recording.camera_ip in self.active_recordings:
                print(f"Already recording for {recording.camera_ip}, skipping.")
                return

            self.active_recordings[recording.camera_ip] = recording

        usage = DiskUsage.from_path(get_recordings_path())
        threshold = 0.10
        while usage.free / usage.total < threshold:
            oldest_recording = self.recording_repository.find_and_delete_oldest_completed()
            if oldest_recording is not None:
                file_path = os.path.join(oldest_recording.path, oldest_recording.name)
                delete_file(file_path)
                self.trigger_orphan_files_cleanup()
                usage = DiskUsage.from_path(get_recordings_path())
            else:
                break

        if camera.always_recording:
            duration = self.always_recording_duration
            segment_duration = duration // 20
            delay_execution(
                func=self.stop_and_rotate_always_recording,
                args=(recording,),
                delay_seconds=duration
            )
        else:
            duration = self.alarm_recording_duration
            segment_duration = duration // 20

        thread = RecordingThread(camera, recording, segment_duration, self.on_recording_completed)
        thread.start()

        with self.lock:
            self.active_threads[recording.camera_ip] = thread

        print(f"Start recording for camera on {recording.camera_ip}")

    def stop_recording(self, recording: Recording):
        with self.lock:
            if recording.camera_ip in self.active_recordings:
                del self.active_recordings[recording.camera_ip]
            thread = self.active_threads.get(recording.camera_ip)
            if thread:
                del self.active_threads[recording.camera_ip]

        if thread:
            thread.stop()
            thread.join(timeout=30)

        print(f"Stopped recording for camera on {recording.camera_ip}")

    def stop_by_camera_ip(self, camera_ip: str):
        with self.lock:
            recording = self.active_recordings.get(camera_ip)
            if recording:
                del self.active_recordings[camera_ip]
            thread = self.active_threads.get(camera_ip)
            if thread:
                del self.active_threads[camera_ip]

        if thread:
            thread.stop()
            thread.join(timeout=30)

        return recording

    def stop_and_rotate_always_recording(self, recording: Recording):
        camera = self.camera_repository.find_by_ip(recording.camera_ip)

        with self.lock:
            if recording.camera_ip not in self.active_recordings:
                return
            if self.active_recordings[recording.camera_ip].id != recording.id:
                return

        self.stop_recording(recording)

        if camera.always_recording:
            try:
                new_recording = self.recording_repository.create(
                    Recording.from_dto(RecordingInputDto(
                        camera_ip=camera.ip,
                        always_recording=True
                    ))
                )
                self.start_recording(new_recording)
                print(f"Rotated to new recording {new_recording.id} for always-on camera {recording.camera_ip}")
            except Exception as e:
                print(f"Error rotating recording for {recording.camera_ip}: {e}")

    def delete_recording_file(self, recording: Recording):
        file_path = os.path.join(recording.path, recording.name)
        delete_file(file_path)

        base_name = os.path.splitext(file_path)[0]
        extension = os.path.splitext(file_path)[1] or '.mkv'

        max_segments = 100
        for i in range(max_segments):
            segment = f"{base_name}_{i:03d}{extension}"
            if os.path.exists(segment):
                delete_file(segment)
            else:
                break

    def get_current_recording_by_camera_ip(self, camera_ip: str):
        with self.lock:
            return self.active_recordings.get(camera_ip)

    def on_recording_completed(self, recording: Recording):
        print(f"Thread completed for recording {recording.id} on camera {recording.camera_ip}")

        with self.lock:
            if recording.camera_ip in self.active_recordings:
                if self.active_recordings[recording.camera_ip].id == recording.id:
                    del self.active_recordings[recording.camera_ip]
            if recording.camera_ip in self.active_threads:
                if self.active_threads[recording.camera_ip].recording.id == recording.id:
                    del self.active_threads[recording.camera_ip]

        try:
            self.recording_repository.set_stopped(recording)
            print(f"Marked recording {recording.id} as completed for camera {recording.camera_ip}")
        except Exception as e:
            print(f"Error marking recording {recording.id} as completed: {e}")

    def trigger_orphan_files_cleanup(self):
        """Trigger async cleanup of orphan recording files."""
        threading.Thread(target=self._cleanup_orphan_files, daemon=True).start()

    def _start_cleanup_scheduler(self):
        """Start the hourly cleanup scheduler."""
        def scheduler_loop():
            print(f"Orphan files cleanup scheduler started (interval: {self.cleanup_interval_seconds}s)")
            while not self._scheduler_stop_event.is_set():
                self._scheduler_stop_event.wait(self.cleanup_interval_seconds)
                if not self._scheduler_stop_event.is_set():
                    print("Running scheduled orphan files cleanup...")
                    self._cleanup_orphan_files()

        self._scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def _cleanup_orphan_files(self):
        """Delete recording files that don't have a corresponding DB entry."""
        with self._cleanup_lock:
            print("Starting orphan files cleanup...")
            deleted_count = 0

            # Get all recording names from DB
            try:
                db_recordings = self.recording_repository.find_all()
                db_recording_names = {rec.name for rec in db_recordings if rec.name}
            except Exception as e:
                print(f"Error fetching recordings from DB: {e}")
                return

            # Get currently active recording names (don't delete files being recorded)
            with self.lock:
                active_names = {rec.name for rec in self.active_recordings.values() if rec.name}

            # Check both recording directories
            for recordings_path in [get_recordings_path(), get_alarm_recordings_path()]:
                if not os.path.exists(recordings_path):
                    continue

                try:
                    files = os.listdir(recordings_path)
                except Exception as e:
                    print(f"Error listing directory {recordings_path}: {e}")
                    continue

                for filename in files:
                    # Skip temporary files
                    if filename.startswith('.concat_') or filename.endswith('.tmp.mkv'):
                        continue

                    # Extract base name (handle segments like file_000.mkv, file_001.mkv)
                    base_name = self._get_base_recording_name(filename)

                    # Skip if this file belongs to an active recording
                    if base_name in active_names or filename in active_names:
                        continue

                    # Delete if no corresponding DB entry exists
                    if base_name not in db_recording_names and filename not in db_recording_names:
                        file_path = os.path.join(recordings_path, filename)
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            print(f"Deleted orphan file: {file_path}")
                        except Exception as e:
                            print(f"Error deleting orphan file {file_path}: {e}")

            print(f"Orphan files cleanup completed. Deleted {deleted_count} files.")

    def _recover_incomplete_recordings(self):
        """Recover recordings interrupted by blackout/restart. Runs in a daemon thread."""
        def recovery_loop():
            # Retry until DB is ready (it may still be starting up)
            incomplete = None
            for attempt in range(10):
                try:
                    incomplete = self.recording_repository.find_incomplete()
                    break
                except Exception:
                    time.sleep(3)

            if incomplete is None:
                print("Startup recovery: could not connect to DB after retries.")
                return

            if not incomplete:
                print("Startup recovery: no incomplete recordings found.")
                return

            print(f"Startup recovery: found {len(incomplete)} incomplete recording(s)")

            for recording in incomplete:
                try:
                    file_path = os.path.join(recording.path, recording.name)
                    base_name = os.path.splitext(file_path)[0]
                    extension = os.path.splitext(file_path)[1] or '.mkv'

                    # Collect unmerged segments (early ones may have been deleted by progressive merge)
                    segments = []
                    consecutive_misses = 0
                    for i in range(1000):
                        segment = f"{base_name}_{i:03d}{extension}"
                        if os.path.exists(segment):
                            segments.append(segment)
                            consecutive_misses = 0
                        else:
                            consecutive_misses += 1
                            if consecutive_misses > 20:
                                break

                    final_exists = os.path.exists(file_path)

                    if not segments and not final_exists:
                        print(f"Startup recovery: no files for recording {recording.id}, deleting DB entry")
                        self.recording_repository.delete_by_id(recording.id)
                        continue

                    if segments:
                        print(f"Startup recovery: merging {len(segments)} segments for recording {recording.id}")
                        for segment in segments:
                            if not os.path.exists(file_path):
                                os.rename(segment, file_path)
                            else:
                                temp_path = file_path + ".tmp.mkv"
                                concat_list = os.path.join(
                                    os.path.dirname(file_path),
                                    f".concat_recovery_{time.time()}.txt"
                                )
                                with open(concat_list, 'w') as f:
                                    f.write(f"file '{os.path.abspath(file_path)}'\n")
                                    f.write(f"file '{os.path.abspath(segment)}'\n")

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
                                    os.replace(temp_path, file_path)
                                    try:
                                        os.remove(segment)
                                    except:
                                        pass
                                else:
                                    print(f"Startup recovery: merge failed for {segment}: {result.stderr.decode()}")
                                    try:
                                        os.remove(temp_path)
                                    except:
                                        pass

                    self.recording_repository.set_stopped(recording)
                    print(f"Startup recovery: completed recording {recording.id}")

                except Exception as e:
                    print(f"Startup recovery: error recovering recording {recording.id}: {e}")

        threading.Thread(target=recovery_loop, daemon=True).start()

    def _get_base_recording_name(self, filename: str) -> str:
        """Extract base recording name from filename (handles segments like file_000.mkv)."""
        # Match pattern like: 2024_01_01_12_00_00_192.168.1.1_000.mkv
        segment_pattern = r'^(.+)_\d{3}(\.[^.]+)$'
        match = re.match(segment_pattern, filename)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        return filename