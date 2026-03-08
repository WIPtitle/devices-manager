import os
import logging
import time
from functools import wraps
from typing import Callable, get_type_hints, List, Tuple

from app.repositories.sensor.impl.sensor_repository_impl import SensorRepositoryImpl

from app.clients.alarm_events_client import AlarmEventsClient
from app.clients.auth_client import AuthClient
from app.clients.gpio_monitor_client import GpioMonitorClient
from app.database.database_connector import DatabaseConnector
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.exceptions.not_implemented_exception import NotImplementedException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.alarm.impl.alarm_manager_impl import AlarmManagerImpl
from app.jobs.detection.detection_manager import DetectionManager
from app.jobs.detection.impl.detection_manager_impl import DetectionManagerImpl
from app.jobs.recording.impl.recordings_manager_impl import RecordingsManagerImpl
from app.jobs.recording.recordings_manager import RecordingsManager
from app.jobs.sensor.impl.sensors_listener_impl import SensorsListenerImpl
from app.jobs.sensor.sensors_listener import SensorsListener
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.camera.impl.camera_repository_impl import CameraRepositoryImpl
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.device_group.impl.device_group_repository_impl import DeviceGroupRepositoryImpl
from app.repositories.recording.impl.recording_repository_impl import RecordingRepositoryImpl
from app.repositories.recording.recording_repository import RecordingRepository
from app.repositories.sensor.sensor_repository import SensorRepository
from app.repositories.system_config.impl.system_config_repository_impl import SystemConfigRepositoryImpl
from app.repositories.system_config.system_config_repository import SystemConfigRepository
from app.services.camera.camera_service import CameraService
from app.services.camera.impl.camera_service_impl import CameraServiceImpl
from app.services.device_group.device_group_service import DeviceGroupService
from app.services.device_group.impl.device_group_service_impl import DeviceGroupServiceImpl
from app.services.recording.impl.recording_service_impl import RecordingServiceImpl
from app.services.recording.recording_service import RecordingService
from app.services.sensor.impl.sensor_service_impl import SensorServiceImpl
from app.services.sensor.sensor_service import SensorService
from app.services.system_config.impl.system_config_service_impl import SystemConfigServiceImpl
from app.services.system_config.system_config_service import SystemConfigService
from app.utils.event_manager import event_manager, EventManager
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bindings = {}

database_connector = DatabaseConnectorImpl()

alarm_events_client = AlarmEventsClient()

# --- Load config from DB ---

system_config_repository = SystemConfigRepositoryImpl(database_connector=database_connector)

# --- Create GPIO clients from DB ---

gpio_servers = system_config_repository.get_all_gpio_servers()
gpio_monitor_clients: List[Tuple[str, GpioMonitorClient]] = []

for gpio_server in gpio_servers:
    client = GpioMonitorClient(gpio_server.url)
    gpio_monitor_clients.append((gpio_server.url, client))
    print(f"Created GPIO Monitor client for {gpio_server.url}")

# --- Apply DB config values at startup ---

def _apply_startup_config():
    """Apply DB config values that need to be set at startup."""
    try:
        tz = system_config_repository.get_config("timezone")
        if tz:
            os.environ["TZ"] = tz
            time.tzset()
            print(f"Applied timezone from DB: {tz}")

        yolo_model = system_config_repository.get_config("detection_yolo_model")
        if yolo_model:
            os.environ["DETECTION_YOLO_MODEL"] = yolo_model
            print(f"Applied YOLO model from DB: {yolo_model}")
    except Exception as e:
        print(f"Warning: failed to apply startup config: {e}")

_apply_startup_config()

# Preload YOLO model in background so it's ready when alarm starts
from app.jobs.detection.impl.detection_model_provider import DetectionModelProvider
DetectionModelProvider.preload()

bindings[EventManager] = event_manager

camera_repository = CameraRepositoryImpl(database_connector=database_connector)
sensor_repository = SensorRepositoryImpl(database_connector=database_connector)
recording_repository = RecordingRepositoryImpl(database_connector=database_connector)
device_group_repository = DeviceGroupRepositoryImpl(database_connector=database_connector)

# Read recording durations from DB
_alarm_duration = system_config_repository.get_config("alarm_recording_duration_seconds")
_always_duration = system_config_repository.get_config("always_recording_duration_seconds")

recording_manager = RecordingsManagerImpl(camera_repository, recording_repository)
# Override config from DB if available
if _alarm_duration:
    recording_manager.alarm_recording_duration = int(_alarm_duration)
if _always_duration:
    recording_manager.always_recording_duration = int(_always_duration)

_detection_confidence = system_config_repository.get_config("detection_confidence")
if _detection_confidence:
    recording_manager.detection_confidence = int(_detection_confidence)
_motion_sensitivity = system_config_repository.get_config("motion_sensitivity")
if _motion_sensitivity:
    recording_manager.motion_sensitivity = int(_motion_sensitivity)
_warning_cooldown = system_config_repository.get_config("warning_cooldown_seconds")
if _warning_cooldown:
    recording_manager.warning_cooldown_seconds = int(_warning_cooldown)

recording_service = RecordingServiceImpl(recording_repository=recording_repository, camera_repository=camera_repository, recording_manager=recording_manager)
alarm_manager = AlarmManagerImpl(alarm_events_client, recording_service, device_group_repository, camera_repository, sensor_repository)
# Override alarm duration from DB if available
if _alarm_duration:
    alarm_manager.alarm_recording_duration = int(_alarm_duration)

sensors_listener = SensorsListenerImpl(alarm_manager, sensor_repository, gpio_monitor_clients)

detection_manager = DetectionManagerImpl(recording_manager, alarm_events_client, camera_repository)
alarm_manager.set_detection_manager(detection_manager)

system_config_service = SystemConfigServiceImpl(
    system_config_repository, device_group_repository, sensor_repository,
    recording_manager, alarm_manager, sensors_listener
)

# camera_service must be created first so recordings (and frame buffers) are running
# before device_group_service recovery tries to start detection workers
camera_service = CameraServiceImpl(camera_repository=camera_repository, recording_service=recording_service)
sensor_service = SensorServiceImpl(sensor_repository=sensor_repository, sensors_listener=sensors_listener)
device_group_service = DeviceGroupServiceImpl(device_group_repository, camera_repository, sensor_repository, alarm_manager, alarm_events_client, detection_manager)

bindings[DatabaseConnector] = database_connector
bindings[AlarmEventsClient] = alarm_events_client
bindings['gpio_monitor_clients'] = gpio_monitor_clients

bindings[CameraRepository] = camera_repository
bindings[RecordingRepository] = recording_repository
bindings[DeviceGroupRepository] = device_group_repository
bindings[SensorRepository] = sensor_repository
bindings[SystemConfigRepository] = system_config_repository

bindings[RecordingsManager] = recording_manager
bindings[AlarmManager] = alarm_manager
bindings[SensorsListener] = sensors_listener
bindings[DetectionManager] = detection_manager

bindings[CameraService] = camera_service
bindings[RecordingService] = recording_service
bindings[DeviceGroupService] = device_group_service
bindings[SensorService] = sensor_service
bindings[SystemConfigService] = system_config_service

bindings[AuthClient] = AuthClient()

# Notify local-audio-manager about current MP3 config on startup
def _sync_mp3_config_to_audio_manager():
    try:
        mp3_servers = system_config_repository.get_all_mp3_servers()
        if not mp3_servers:
            return
        payload = []
        for s in mp3_servers:
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

        import httpx
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "http://local-audio-manager:8000/internal/reload-mp3-config",
                json=payload,
            )
            response.raise_for_status()
            print(f"Synced MP3 config to local-audio-manager ({len(payload)} servers)")
    except Exception as e:
        print(f"Warning: failed to sync MP3 config to local-audio-manager: {e}")

threading.Thread(target=_sync_mp3_config_to_audio_manager, daemon=True).start()


def resolve(interface):
    implementation = bindings[interface]
    if implementation is None:
        raise NotImplementedException(f"No binding found for {interface}")
    return implementation


def inject(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        type_hints = get_type_hints(func)
        for name, param_type in type_hints.items():
            if param_type in bindings:
                kwargs[name] = resolve(param_type)
        return func(*args, **kwargs)
    return wrapper
