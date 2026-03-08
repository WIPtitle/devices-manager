import threading
from typing import Sequence

from app.clients.alarm_events_client import AlarmEventsClient
from app.jobs.detection.detection_manager import DetectionManager
from app.jobs.detection.impl.motion_detection_worker import MotionDetectionWorker
from app.jobs.recording.recordings_manager import RecordingsManager
from app.repositories.camera.camera_repository import CameraRepository


class DetectionManagerImpl(DetectionManager):
    def __init__(self,
                 recordings_manager: RecordingsManager,
                 alarm_events_client: AlarmEventsClient,
                 camera_repository: CameraRepository):
        self.recordings_manager = recordings_manager
        self.alarm_events_client = alarm_events_client
        self.camera_repository = camera_repository
        self.active_workers: dict[str, MotionDetectionWorker] = {}
        self._warning_enabled = False
        self._lock = threading.Lock()

    def on_group_start_listening(self, camera_ips: Sequence[str]):
        with self._lock:
            self._warning_enabled = True

        for camera_ip in camera_ips:
            if camera_ip in self.active_workers:
                continue
            camera = self.camera_repository.find_by_ip(camera_ip)
            if camera is None or not camera.always_recording or camera.detection_mode is None:
                continue
            frame_buffer = self.recordings_manager.get_frame_buffer(camera.ip)
            if frame_buffer is not None:
                worker = MotionDetectionWorker(
                    camera=camera,
                    frame_buffer=frame_buffer,
                    alarm_events_client=self.alarm_events_client,
                    detection_manager=self,
                    detection_confidence=self.recordings_manager.detection_confidence,
                    motion_sensitivity=self.recordings_manager.motion_sensitivity,
                    warning_cooldown_seconds=self.recordings_manager.warning_cooldown_seconds,
                )
                worker.start()
                self.active_workers[camera.ip] = worker
            else:
                print(f"No frame buffer available for camera {camera_ip}, skipping detection")

        if self.active_workers:
            print(f"Motion detection active on {len(self.active_workers)} camera(s)")

    def on_group_leave_listening(self):
        with self._lock:
            self._warning_enabled = False
        print("Detection warnings disabled (group left LISTENING state)")

    def on_all_groups_idle(self):
        with self._lock:
            self._warning_enabled = False
        for worker in self.active_workers.values():
            worker.stop()
        count = len(self.active_workers)
        self.active_workers.clear()
        if count > 0:
            print(f"Motion detection stopped on {count} camera(s)")

    def is_warning_enabled(self) -> bool:
        with self._lock:
            return self._warning_enabled
