import os
import logging
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
from app.services.camera.camera_service import CameraService
from app.services.camera.impl.camera_service_impl import CameraServiceImpl
from app.services.device_group.device_group_service import DeviceGroupService
from app.services.device_group.impl.device_group_service_impl import DeviceGroupServiceImpl
from app.services.recording.impl.recording_service_impl import RecordingServiceImpl
from app.services.recording.recording_service import RecordingService
from app.services.sensor.impl.sensor_service_impl import SensorServiceImpl
from app.services.sensor.sensor_service import SensorService
from app.utils.event_manager import event_manager, EventManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bindings = {}

database_connector = DatabaseConnectorImpl()

alarm_events_client = AlarmEventsClient()

gpio_urls = os.getenv("GPIO_MONITOR_URLS", "http://localhost:8787")
gpio_monitor_urls = [url.strip() for url in gpio_urls.split(",")]
gpio_monitor_clients: List[Tuple[str, GpioMonitorClient]] = []

for gpio_url in gpio_monitor_urls:
    client = GpioMonitorClient(gpio_url)
    gpio_monitor_clients.append((gpio_url, client))
    print(f"Created GPIO Monitor client for {gpio_url}")

bindings[EventManager] = event_manager

camera_repository = CameraRepositoryImpl(database_connector=database_connector)
sensor_repository = SensorRepositoryImpl(database_connector=database_connector)
recording_repository = RecordingRepositoryImpl(database_connector=database_connector)
device_group_repository = DeviceGroupRepositoryImpl(database_connector=database_connector)

recording_manager = RecordingsManagerImpl(camera_repository, recording_repository)
recording_service = RecordingServiceImpl(recording_repository=recording_repository, camera_repository=camera_repository, recording_manager=recording_manager)
alarm_manager = AlarmManagerImpl(alarm_events_client, recording_service, device_group_repository, camera_repository, sensor_repository)

sensors_listener = SensorsListenerImpl(alarm_manager, sensor_repository, gpio_monitor_clients)

device_group_service = DeviceGroupServiceImpl(device_group_repository, camera_repository, sensor_repository, alarm_manager, alarm_events_client)
sensor_service = SensorServiceImpl(sensor_repository=sensor_repository, sensors_listener=sensors_listener)
camera_service = CameraServiceImpl(camera_repository=camera_repository, recording_service=recording_service)

bindings[DatabaseConnector] = database_connector
bindings[AlarmEventsClient] = alarm_events_client
bindings['gpio_monitor_clients'] = gpio_monitor_clients

bindings[CameraRepository] = camera_repository
bindings[RecordingRepository] = recording_repository
bindings[DeviceGroupRepository] = device_group_repository
bindings[SensorRepository] = sensor_repository

bindings[RecordingsManager] = recording_manager
bindings[AlarmManager] = alarm_manager
bindings[SensorsListener] = sensors_listener

bindings[CameraService] = camera_service
bindings[RecordingService] = recording_service
bindings[DeviceGroupService] = device_group_service
bindings[SensorService] = sensor_service

bindings[AuthClient] = AuthClient()


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