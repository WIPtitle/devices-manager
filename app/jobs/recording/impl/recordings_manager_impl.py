import glob
import os
from threading import Lock, Event

from app.jobs.recording.impl.recording_thread import RecordingThread
from app.jobs.recording.recordings_manager import RecordingsManager
from app.models.disk_usage import DiskUsage
from app.models.recording import Recording, get_recordings_path, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository
from app.utils.delayed_execution import delay_execution


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
        self.active_recordings = {}
        self.active_threads = {}
        self.lock = Lock()

        self.alarm_recording_duration = int(os.getenv('ALARM_RECORDING_DURATION_SECONDS', '120'))
        self.always_recording_duration = int(os.getenv('ALWAYS_RECORDING_DURATION_SECONDS', '3600'))

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

        if camera.always_recording:
            duration = self.always_recording_duration
            segment_duration = duration // 10
            delay_execution(
                func=self.stop_and_rotate_always_recording,
                args=(recording,),
                delay_seconds=duration
            )
        else:
            duration = self.alarm_recording_duration
            segment_duration = duration // 10

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