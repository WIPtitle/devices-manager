import time
import threading
import logging
from typing import Dict, Set
from datetime import datetime, timedelta

from app.models.camera import Camera
from app.models.recording import Recording, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository

logger = logging.getLogger(__name__)


class RecordingHealthMonitor:
    def __init__(self, camera_repository: CameraRepository,
                 recording_repository: RecordingRepository,
                 recording_manager):
        self.camera_repository = camera_repository
        self.recording_repository = recording_repository
        self.recording_manager = recording_manager
        self.running = False
        self.monitor_thread = None
        self.camera_retry_count: Dict[str, int] = {}
        self.camera_last_check: Dict[str, datetime] = {}
        self.max_retry_attempts = 5
        self.retry_delay_seconds = 10
        self.health_check_interval = 30

    def start(self):
        if self.running:
            return
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Recording health monitor started")

    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Recording health monitor stopped")

    def _monitor_loop(self):
        while self.running:
            try:
                self._check_all_recordings()
                self._check_disconnected_cameras()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                time.sleep(5)

    def _check_all_recordings(self):
        try:
            cameras = self.camera_repository.find_all()
            for camera in cameras:
                if camera.always_recording:
                    self._ensure_camera_recording(camera)
        except Exception as e:
            logger.error(f"Error checking recordings: {e}")

    def _ensure_camera_recording(self, camera: Camera):
        if not self.recording_manager.is_recording(camera.ip):
            logger.warning(f"Camera {camera.ip} should be recording but isn't. Starting recording...")

            retry_count = self.camera_retry_count.get(camera.ip, 0)
            if retry_count >= self.max_retry_attempts:
                last_check = self.camera_last_check.get(camera.ip)
                if last_check and datetime.now() - last_check < timedelta(minutes=30):
                    logger.error(f"Camera {camera.ip} exceeded max retries. Waiting before next attempt...")
                    return
                else:
                    self.camera_retry_count[camera.ip] = 0

            try:
                if camera.is_reachable():
                    recording = Recording.from_dto(RecordingInputDto(
                        camera_ip=camera.ip,
                        always_recording=True
                    ))
                    recording = self.recording_repository.create(recording)
                    self.recording_manager.start_recording(recording)
                    self.camera_retry_count[camera.ip] = 0
                    logger.info(f"Successfully restarted recording for camera {camera.ip}")
                else:
                    self.camera_retry_count[camera.ip] = retry_count + 1
                    self.camera_last_check[camera.ip] = datetime.now()
                    logger.warning(
                        f"Camera {camera.ip} is not reachable. Retry count: {self.camera_retry_count[camera.ip]}")
            except Exception as e:
                logger.error(f"Failed to restart recording for camera {camera.ip}: {e}")
                self.camera_retry_count[camera.ip] = retry_count + 1

    def _check_disconnected_cameras(self):
        cameras_to_check = []
        for camera_ip, retry_count in self.camera_retry_count.items():
            if retry_count > 0:
                last_check = self.camera_last_check.get(camera_ip, datetime.min)
                if datetime.now() - last_check > timedelta(seconds=self.retry_delay_seconds):
                    cameras_to_check.append(camera_ip)

        for camera_ip in cameras_to_check:
            try:
                camera = self.camera_repository.find_by_ip(camera_ip)
                if camera.always_recording:
                    logger.info(f"Retrying camera {camera_ip}...")
                    self._ensure_camera_recording(camera)
            except Exception as e:
                logger.error(f"Error retrying camera {camera_ip}: {e}")