import glob
import os
from threading import Lock
import time

from app.jobs.recording.impl.recording_thread import RecordingThread
from app.jobs.recording.recordings_manager import RecordingsManager
from app.models.disk_usage import DiskUsage
from app.models.recording import Recording, get_recordings_path, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository


def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        return os.path.basename(file_path)
    return None


def get_oldest_file():
    files = glob.glob(os.path.join(get_recordings_path(), '*'))
    files = [f for f in files if not f.startswith('.concat_')]
    if files:
        oldest_file = min(files, key=os.path.getctime)
        return oldest_file
    return None


class RecordingsManagerImpl(RecordingsManager):
    def __init__(self, camera_repository: CameraRepository, recording_repository: RecordingRepository):
        self.camera_repository = camera_repository
        self.recording_repository = recording_repository
        self.threads = []
        self.threads_lock = Lock()
        self.stopped_recordings = set()
        self.persistent_recordings = {}

    def is_recording(self, camera_ip: str):
        with self.threads_lock:
            self.threads = [t for t in self.threads if t.is_alive()]
            return any(t.recording.camera_ip == camera_ip and t.recording.id not in self.stopped_recordings for t in
                       self.threads)

    def start_recording(self, recording: Recording):
        with self.threads_lock:
            if recording.id in self.stopped_recordings:
                return

            active_thread = None
            for t in self.threads:
                if t.recording.camera_ip == recording.camera_ip and t.is_alive() and t.recording.id not in self.stopped_recordings:
                    active_thread = t
                    break

            if active_thread:
                print(f"Already recording for {recording.camera_ip}, skipping.")
                return

        camera = self.camera_repository.find_by_ip(recording.camera_ip)

        usage = DiskUsage.from_path(get_recordings_path())
        threshold = 0.10
        while usage.free / usage.total < threshold:
            oldest_file = get_oldest_file()
            if oldest_file is not None:
                deleted_filename = delete_file(oldest_file)
                try:
                    rec = self.recording_repository.find_by_name(deleted_filename)
                    if rec:
                        self.recording_repository.delete_by_id(rec.id)
                except:
                    pass
                usage = DiskUsage.from_path(get_recordings_path())
            else:
                break

        with self.threads_lock:
            self.threads = [t for t in self.threads if t.is_alive() or t.recording.id not in self.stopped_recordings]

            thread = RecordingThread(camera, recording, self.thread_error_callback)
            thread.start()
            self.threads.append(thread)

            if camera.always_recording:
                self.persistent_recordings[recording.camera_ip] = recording

            print(f"Start recording for camera on {recording.camera_ip}")

    def stop_recording(self, recording: Recording):
        with self.threads_lock:
            self.stopped_recordings.add(recording.id)

            if recording.camera_ip in self.persistent_recordings:
                if self.persistent_recordings[recording.camera_ip].id == recording.id:
                    del self.persistent_recordings[recording.camera_ip]

            for thread in self.threads:
                if thread.recording.id == recording.id:
                    thread.stop()
                    break

        print(f"Stopped recording for camera on {recording.camera_ip}")

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
        with self.threads_lock:
            for thread in self.threads:
                if thread.recording.camera_ip == camera_ip and thread.is_alive() and thread.recording.id not in self.stopped_recordings:
                    return thread.recording
        return None

    def thread_error_callback(self, recording: Recording):
        if recording.id in self.stopped_recordings:
            return

        if recording.camera_ip not in self.persistent_recordings and not self._should_continue_alarm(recording):
            return

        print(f"Thread error for camera on {recording.camera_ip}, checking if restart needed...")

        time.sleep(2)

        with self.threads_lock:
            if recording.id in self.stopped_recordings:
                return

            self.threads = [t for t in self.threads if t.recording.id != recording.id or t.is_alive()]

            if recording.camera_ip in self.persistent_recordings:
                if self.persistent_recordings[recording.camera_ip].id != recording.id:
                    return

            active_for_camera = any(
                t.recording.camera_ip == recording.camera_ip and
                t.is_alive() and
                t.recording.id not in self.stopped_recordings
                for t in self.threads
            )

            if active_for_camera:
                return

        try:
            camera = self.camera_repository.find_by_ip(recording.camera_ip)

            if camera.always_recording or self._should_continue_alarm(recording):
                new_recording = self.recording_repository.create(
                    Recording.from_dto(RecordingInputDto(
                        camera_ip=camera.ip,
                        always_recording=camera.always_recording
                    ))
                )
                self.start_recording(new_recording)
        except Exception as e:
            print(f"Error restarting recording for {recording.camera_ip}: {e}")

    def _should_continue_alarm(self, recording: Recording):
        if not recording.always_recording:
            created_time = recording.created_at if hasattr(recording, 'created_at') else 0
            if isinstance(created_time, str):
                try:
                    import datetime
                    created_time = datetime.datetime.fromisoformat(created_time).timestamp()
                except:
                    created_time = 0
            elapsed = time.time() - created_time
            return elapsed < 120
        return False