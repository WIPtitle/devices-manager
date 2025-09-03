import glob
import os
import logging
from threading import Lock
from typing import Optional

from app.jobs.recording.impl.resilient_recording_thread import ResilientRecordingThread
from app.jobs.recording.impl.recording_health_monitor import RecordingHealthMonitor
from app.jobs.recording.recordings_manager import RecordingsManager
from app.models.disk_usage import DiskUsage
from app.models.recording import Recording, get_recordings_path, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository

logger = logging.getLogger(__name__)


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
        self.threads_lock = Lock()
        self.health_monitor = RecordingHealthMonitor(
            camera_repository=camera_repository,
            recording_repository=recording_repository,
            recording_manager=self
        )
        self.health_monitor.start()
        logger.info("RecordingsManager initialized with health monitoring")

    def is_recording(self, camera_ip: str):
        with self.threads_lock:
            self.threads = [t for t in self.threads if t.is_alive()]
            return any(t.recording.camera_ip == camera_ip for t in self.threads)

    def start_recording(self, recording: Recording):
        if self.is_recording(recording.camera_ip):
            logger.info(f"Already recording for {recording.camera_ip}, skipping.")
            return

        camera = self.camera_repository.find_by_ip(recording.camera_ip)

        usage = DiskUsage.from_path(get_recordings_path())
        threshold = 0.10
        while usage.free / usage.total < threshold:
            oldest_file = get_oldest_file()
            if oldest_file is None:
                logger.error("No space available and no files to delete!")
                break
            deleted_filename = delete_file(oldest_file)
            try:
                rec = self.recording_repository.find_by_name(deleted_filename)
                self.recording_repository.delete_by_id(rec.id)
            except Exception as e:
                logger.error(f"Error deleting recording from DB: {e}")
            usage = DiskUsage.from_path(get_recordings_path())

        with self.threads_lock:
            thread = ResilientRecordingThread(
                camera=camera,
                recording=recording,
                on_complete_callback=self.recording_complete_callback
            )
            thread.start()
            self.threads.append(thread)
            logger.info(f"Started recording for camera {recording.camera_ip}")

    def stop_recording(self, recording: Recording):
        with self.threads_lock:
            for thread in self.threads:
                if thread.recording.id == recording.id:
                    thread.stop()
                    self.threads.remove(thread)
                    break
        logger.info(f"Stopped recording for camera {recording.camera_ip}")

    def delete_recording_file(self, recording: Recording):
        delete_file(os.path.join(recording.path, recording.name))

    def get_current_recording_by_camera_ip(self, camera_ip: str) -> Optional[Recording]:
        with self.threads_lock:
            for thread in self.threads:
                if thread.recording.camera_ip == camera_ip and thread.is_alive():
                    return thread.recording
        return None

    def recording_complete_callback(self, recording: Recording):
        logger.info(f"Recording completed for camera {recording.camera_ip}")

        with self.threads_lock:
            self.threads = [t for t in self.threads if t.recording.id != recording.id or t.is_alive()]

        try:
            camera = self.camera_repository.find_by_ip(recording.camera_ip)

            if camera.always_recording:
                logger.info(f"Restarting always-on recording for camera {recording.camera_ip}")
                new_recording = self.recording_repository.create(
                    Recording.from_dto(RecordingInputDto(
                        camera_ip=camera.ip,
                        always_recording=camera.always_recording
                    ))
                )
                self.start_recording(new_recording)
        except Exception as e:
            logger.error(f"Error in recording complete callback for {recording.camera_ip}: {e}")

    def __del__(self):
        if hasattr(self, 'health_monitor'):
            self.health_monitor.stop()