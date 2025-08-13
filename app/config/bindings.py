import os
from functools import wraps
from typing import Callable, get_type_hints

from rabbitmq_sdk.client.impl.rabbitmq_client_impl import RabbitMQClientImpl
from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.enums.service import Service

from app.clients.auth_client import AuthClient
from app.clients.gpio_monitor_client import GpioMonitorClient
from app.database.database_connector import DatabaseConnector
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.exceptions.not_implemented_exception import NotImplementedException
from app.exceptions.sensors_listener_exception import SensorsListenerException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.alarm.impl.alarm_manager_impl import AlarmManagerImpl
from app.jobs.sensor.impl.sensors_listener_impl import SensorsListenerImpl
from app.jobs.sensor.sensors_listener import SensorsListener
from app.jobs.recording.impl.recordings_manager_impl import RecordingsManagerImpl
from app.jobs.recording.recordings_manager import RecordingsManager
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.camera.impl.camera_repository_impl import CameraRepositoryImpl
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.device_group.impl.device_group_repository_impl import DeviceGroupRepositoryImpl
from app.repositories.sensor.impl.sensor_repository_impl import SensorRepositoryImpl
from app.repositories.sensor.sensor_repository import SensorRepository
from app.repositories.recording.impl.recording_repository_impl import RecordingRepositoryImpl
from app.repositories.recording.recording_repository import RecordingRepository
from app.services.camera.camera_service import CameraService
from app.services.camera.impl.camera_service_impl import CameraServiceImpl
from app.services.device_group.device_group_service import DeviceGroupService
from app.services.device_group.impl.device_group_service_impl import DeviceGroupServiceImpl
from app.services.sensor.impl.sensor_service_impl import SensorServiceImpl
from app.services.sensor.sensor_service import SensorService
from app.services.recording.impl.recording_service_impl import RecordingServiceImpl
from app.services.recording.recording_service import RecordingService
from app.utils.read_credentials import read_credentials

bindings = {}

# Create instances only one time
database_connector = DatabaseConnectorImpl()

rabbit_credentials = read_credentials(os.getenv('RBBT_CREDENTIALS_FILE'))
rabbitmq_client = RabbitMQClientImpl.from_config(
    host=os.getenv("RABBITMQ_HOSTNAME"),  # using container name as host instead of ip
    port=5672,
    username=rabbit_credentials['RABBITMQ_USER'],
    password=rabbit_credentials['RABBITMQ_PASSWORD']
).with_current_service(Service.DEVICES_MANAGER)

# GPIO Monitor Client
gpio_monitor_client = GpioMonitorClient()

# Repositories
camera_repository = CameraRepositoryImpl(database_connector=database_connector)
sensor_repository = SensorRepositoryImpl(database_connector=database_connector)
recording_repository = RecordingRepositoryImpl(database_connector=database_connector)
device_group_repository = DeviceGroupRepositoryImpl(database_connector=database_connector)

# Managers and Services
recording_manager = RecordingsManagerImpl(camera_repository, recording_repository)
recording_service = RecordingServiceImpl(recording_repository=recording_repository, camera_repository=camera_repository, recording_manager=recording_manager)
alarm_manager = AlarmManagerImpl(rabbitmq_client, recording_service, device_group_repository, camera_repository, sensor_repository)
sensors_listener = SensorsListenerImpl(alarm_manager, sensor_repository, gpio_monitor_client)
device_group_service = DeviceGroupServiceImpl(device_group_repository, camera_repository, sensor_repository, alarm_manager, rabbitmq_client)
sensor_service = SensorServiceImpl(sensor_repository=sensor_repository, sensors_listener=sensors_listener)
camera_service = CameraServiceImpl(camera_repository=camera_repository, recording_service=recording_service)

# Put them in an interface -> instance dict so they will be used everytime a dependency is required
bindings[DatabaseConnector] = database_connector
bindings[RabbitMQClient] = rabbitmq_client
bindings[GpioMonitorClient] = gpio_monitor_client

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