import glob
import os

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
    if files:
        oldest_file = min(files, key=os.path.getctime)
        return oldest_file
    return None


class RecordingsManagerImpl(RecordingsManager):
    def __init__(self, camera_repository: CameraRepository, recording_repository: RecordingRepository):
        self.camera_repository = camera_repository
        self.recording_repository = recording_repository
        self.threads = []


    def is_recording(self, camera_ip: str):
        for thread in self.threads:
            if thread.recording.camera_ip == camera_ip:
                return True
        return False


    def start_recording(self, recording: Recording):
        camera = self.camera_repository.find_by_ip(recording.camera_ip)

        # Delete the oldest file if free space is less than 10%
        usage = DiskUsage.from_path(get_recordings_path())
        threshold = 0.10
        if usage.free / usage.total < threshold:
            oldest_file = get_oldest_file()
            if oldest_file is not None:
                deleted_filename = delete_file(oldest_file)
                recording = self.recording_repository.find_by_name(deleted_filename)
                self.recording_repository.delete_by_id(recording.id)

        thread = RecordingThread(camera, recording, self.thread_error_callback)
        thread.start()
        self.threads.append(thread)
        print(f"Start recording for camera on {recording.camera_ip}")


    def stop_recording(self, recording: Recording):
        for thread in self.threads:
            if thread.recording.id == recording.id:
                thread.stop()
                self.threads.remove(thread)
                break
        print(f"Stopped recording for camera on {recording.camera_ip}")


    def delete_recording_file(self, recording: Recording):
        delete_file(recording.path + "/" + recording.name)


    def get_current_recording_by_camera_ip(self, camera_ip: str):
        for thread in self.threads:
            if thread.recording.camera_ip == camera_ip:
                return thread.recording
        return None


    def thread_error_callback(self, recording: Recording):
        # no need to restart since restart operation is already scheduled for the camera ip, just
        # create a new recording and start it so if something fails we will have two separate files, who cares
        print(f"Error while recording for camera on {recording.camera_ip}, restarting...")

        camera = self.camera_repository.find_by_ip(recording.camera_ip)  # will throw if not found
        recording = self.recording_repository.create(Recording.from_dto(RecordingInputDto(camera_ip=camera.ip, always_recording=camera.always_recording)))
        self.start_recording(recording)

