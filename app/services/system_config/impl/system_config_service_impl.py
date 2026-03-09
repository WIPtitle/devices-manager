import os
from typing import Sequence

import httpx

from app.clients.gpio_monitor_client import GpioMonitorClient
from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.detection.impl.detection_model_provider import DetectionModelProvider
from app.jobs.detection.impl.notification_scheduler import NotificationScheduler
from app.jobs.recording.recordings_manager import RecordingsManager
from app.jobs.sensor.sensors_listener import SensorsListener
from app.models.system_config import GpioServer, Mp3Server
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.sensor.sensor_repository import SensorRepository
from app.repositories.system_config.system_config_repository import SystemConfigRepository
from app.services.system_config.system_config_service import SystemConfigService

VALID_CONFIG_KEYS = {
    "alarm_recording_duration_seconds",
    "always_recording_duration_seconds",
    "warning_cooldown_seconds",
    "warning_notification_delay_seconds",
    "detection_yolo_model",
    "detection_confidence",
    "motion_sensitivity",
}

VALID_YOLO_MODELS = [
    "yolo11n", "yolo11s", "yolo11m", "yolo11l", "yolo11x",
    "yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x",
    "yolo26n", "yolo26s", "yolo26m", "yolo26l", "yolo26x",
]


class SystemConfigServiceImpl(SystemConfigService):
    def __init__(self,
                 system_config_repository: SystemConfigRepository,
                 device_group_repository: DeviceGroupRepository,
                 sensor_repository: SensorRepository,
                 recordings_manager: RecordingsManager,
                 alarm_manager: AlarmManager,
                 sensors_listener: SensorsListener,
                 notification_scheduler: NotificationScheduler):
        self.system_config_repository = system_config_repository
        self.device_group_repository = device_group_repository
        self.sensor_repository = sensor_repository
        self.recordings_manager = recordings_manager
        self.alarm_manager = alarm_manager
        self.sensors_listener = sensors_listener
        self.notification_scheduler = notification_scheduler

    def _ensure_all_groups_idle(self):
        if not self.device_group_repository.are_all_groups_idle():
            raise BadRequestException("Can't modify configuration while not idle")

    def get_all_config(self) -> dict:
        configs = self.system_config_repository.get_all_config()
        return {c.key: c.value for c in configs}

    def update_config(self, key: str, value: str):
        self._ensure_all_groups_idle()

        if key not in VALID_CONFIG_KEYS:
            raise BadRequestException(f"Unknown configuration key: {key}")

        value = value.strip()
        if not value:
            raise BadRequestException("Value cannot be empty")

        self._validate_config_value(key, value)
        self.system_config_repository.set_config(key, value)
        self._apply_config_change(key, value)

    def _validate_config_value(self, key: str, value: str):
        if key in ("alarm_recording_duration_seconds", "always_recording_duration_seconds"):
            try:
                v = int(value)
                if v < 10:
                    raise BadRequestException(f"{key} must be at least 10 seconds")
            except ValueError:
                raise BadRequestException(f"{key} must be an integer")

        elif key in ("warning_cooldown_seconds", "warning_notification_delay_seconds"):
            try:
                v = int(value)
                if v < 0:
                    raise BadRequestException(f"{key} must be >= 0")
            except ValueError:
                raise BadRequestException(f"{key} must be an integer")

        elif key == "detection_yolo_model":
            if value not in VALID_YOLO_MODELS:
                raise BadRequestException(f"Unknown YOLO model: {value}. Valid: {', '.join(VALID_YOLO_MODELS)}")

        elif key in ("detection_confidence", "motion_sensitivity"):
            try:
                v = int(value)
                if v < 1 or v > 100:
                    raise BadRequestException(f"{key} must be between 1 and 100")
            except ValueError:
                raise BadRequestException(f"{key} must be an integer")

    def _apply_config_change(self, key: str, value: str):
        if key == "alarm_recording_duration_seconds":
            v = int(value)
            self.recordings_manager.alarm_recording_duration = v
            self.alarm_manager.alarm_recording_duration = v
            print(f"Config updated: alarm_recording_duration_seconds = {v}")

        elif key == "always_recording_duration_seconds":
            self.recordings_manager.always_recording_duration = int(value)
            print(f"Config updated: always_recording_duration_seconds = {value}")

        elif key == "detection_yolo_model":
            DetectionModelProvider.reload(value)
            print(f"Config updated: detection_yolo_model = {value}")

        elif key == "detection_confidence":
            self.recordings_manager.detection_confidence = int(value)
            print(f"Config updated: detection_confidence = {value}%")

        elif key == "motion_sensitivity":
            self.recordings_manager.motion_sensitivity = int(value)
            print(f"Config updated: motion_sensitivity = {value}%")

        elif key == "warning_cooldown_seconds":
            self.recordings_manager.warning_cooldown_seconds = int(value)
            print(f"Config updated: warning_cooldown_seconds = {value}")

        elif key == "warning_notification_delay_seconds":
            self.notification_scheduler.delay_seconds = int(value)
            print(f"Config updated: warning_notification_delay_seconds = {value}")

    # --- GPIO Servers ---

    def get_all_gpio_servers(self) -> Sequence[GpioServer]:
        return self.system_config_repository.get_all_gpio_servers()

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Replace localhost/127.0.0.1 with host.docker.internal for Docker networking."""
        return url.replace("://localhost", "://host.docker.internal") \
                   .replace("://127.0.0.1", "://host.docker.internal")

    def create_gpio_server(self, server: GpioServer) -> GpioServer:
        self._ensure_all_groups_idle()

        if not server.url or not server.url.strip():
            raise BadRequestException("URL cannot be empty")
        server.url = self._normalize_url(server.url.strip())

        # Verify server is reachable and is a GPIO monitor
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{server.url}/api/pins")
                response.raise_for_status()
                data = response.json()
                if "monitored" not in data:
                    raise BadRequestException("Server responded but is not a GPIO monitor")
        except BadRequestException:
            raise
        except Exception as e:
            raise BadRequestException(f"Cannot reach GPIO monitor at {server.url}: {e}")

        created = self.system_config_repository.create_gpio_server(server)

        # Create and start a new GPIO monitor client
        client = GpioMonitorClient(server.url)
        self.sensors_listener.gpio_clients[server.url] = client
        client.start()
        print(f"Created and started GPIO Monitor client for {server.url}")

        return created

    def delete_gpio_server(self, server_id: int):
        self._ensure_all_groups_idle()

        servers = self.system_config_repository.get_all_gpio_servers()
        server = next((s for s in servers if s.id == server_id), None)
        if not server:
            raise BadRequestException("GPIO server not found")

        # Check if any sensors reference this server URL
        all_sensors = self.sensor_repository.find_all()
        sensors_using = [s for s in all_sensors if s.gpio_server_url == server.url]
        if sensors_using:
            raise BadRequestException(
                f"Cannot delete: {len(sensors_using)} sensor(s) use this GPIO server"
            )

        # Stop and remove the client
        client = self.sensors_listener.gpio_clients.get(server.url)
        if client:
            client.stop()
            del self.sensors_listener.gpio_clients[server.url]
            print(f"Stopped and removed GPIO Monitor client for {server.url}")

        self.system_config_repository.delete_gpio_server(server_id)

    # --- MP3 Servers ---

    def get_all_mp3_servers(self) -> Sequence[Mp3Server]:
        return self.system_config_repository.get_all_mp3_servers()

    def create_mp3_server(self, server: Mp3Server) -> Mp3Server:
        self._ensure_all_groups_idle()

        if not server.url or not server.url.strip():
            raise BadRequestException("URL cannot be empty")
        server.url = self._normalize_url(server.url.strip())

        # Verify server is reachable and is an MP3 player server
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{server.url}/api/status")
                response.raise_for_status()
                data = response.json()
                if "playing" not in data:
                    raise BadRequestException("Server responded but is not an MP3 player server")
        except BadRequestException:
            raise
        except Exception as e:
            raise BadRequestException(f"Cannot reach MP3 player server at {server.url}: {e}")

        created = self.system_config_repository.create_mp3_server(server)
        self._notify_audio_manager_reload()
        return created

    def update_mp3_server(self, server: Mp3Server) -> Mp3Server:
        self._ensure_all_groups_idle()
        updated = self.system_config_repository.update_mp3_server(server)
        self._notify_audio_manager_reload()
        return updated

    def delete_mp3_server(self, server_id: int):
        self._ensure_all_groups_idle()
        self.system_config_repository.delete_mp3_server(server_id)
        self._notify_audio_manager_reload()

    def _notify_audio_manager_reload(self):
        """Notify local-audio-manager to reload its MP3 server configuration."""
        servers = self.system_config_repository.get_all_mp3_servers()
        payload = []
        for s in servers:
            types = []
            if s.audio_type_alarm:
                types.append("ALARM")
            if s.audio_type_waiting:
                types.append("WAITING")
            if s.audio_type_warning:
                types.append("WARNING")
            payload.append({
                "url": s.url,
                "types": types,
                "volume_alarm": s.volume_alarm,
                "volume_waiting": s.volume_waiting,
                "volume_warning": s.volume_warning,
            })

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    "http://local-audio-manager:8000/internal/reload-mp3-config",
                    json=payload,
                )
                response.raise_for_status()
                print(f"Notified local-audio-manager to reload MP3 config ({len(payload)} servers)")
        except Exception as e:
            print(f"Warning: failed to notify local-audio-manager about MP3 config change: {e}")
