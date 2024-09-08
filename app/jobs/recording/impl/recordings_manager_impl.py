from app.jobs.recording.impl.recording_thread import RecordingThread
from app.jobs.recording.recordings_manager import RecordingsManager

from app.models.recording import Recording
from app.repositories.camera.camera_repository import CameraRepository


class RecordingsManagerImpl(RecordingsManager):
    def __init__(self, camera_repository: CameraRepository):
        self.camera_repository = camera_repository
        self.threads = []


    def start_recording(self, recording: Recording):
        camera = self.camera_repository.find_by_ip(recording.camera_ip)
        thread = RecordingThread(camera, recording)
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
