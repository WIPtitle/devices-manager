import os
from functools import wraps
from typing import Callable, get_type_hints

from rabbitmq_sdk.client.impl.rabbitmq_client_impl import RabbitMQClientImpl
from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.enums.service import Service

from app.database.database_connector import DatabaseConnector
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.exceptions.not_implemented_exception import NotImplementedException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.alarm.impl.alarm_manager_impl import AlarmManagerImpl
from app.jobs.camera.cameras_listener import CamerasListener
from app.jobs.camera.impl.cameras_listener_impl import CamerasListenerImpl
from app.jobs.recording.impl.recordings_manager_impl import RecordingsManagerImpl
from app.jobs.recording.recordings_manager import RecordingsManager
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.camera.impl.camera_repository_impl import CameraRepositoryImpl
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.device_group.impl.device_group_repository_impl import DeviceGroupRepositoryImpl
from app.repositories.recording.impl.recording_repository_impl import RecordingRepositoryImpl
from app.repositories.recording.recording_repository import RecordingRepository
from app.services.camera.camera_service import CameraService
from app.services.camera.impl.camera_service_impl import CameraServiceImpl
from app.services.device_group.device_group_service import DeviceGroupService
from app.services.device_group.impl.device_group_service_impl import DeviceGroupServiceImpl
from app.services.recording.impl.recording_service_impl import RecordingServiceImpl
from app.services.recording.recording_service import RecordingService
from app.utils.read_credentials import read_credentials
from app.jobs.reed.impl.reeds_listener_impl import ReedsListenerImpl
from app.jobs.reed.reeds_listener import ReedsListener
from app.repositories.reed.impl.reed_repository_impl import ReedRepositoryImpl
from app.repositories.reed.reed_repository import ReedRepository
from app.services.reed.impl.reed_service_impl import ReedServiceImpl
from app.services.reed.reed_service import ReedService


bindings = { }

# Create instances only one time
database_connector = DatabaseConnectorImpl()

rabbit_credentials = read_credentials(os.getenv('RBBT_CREDENTIALS_FILE'))
rabbitmq_client = RabbitMQClientImpl.from_config(
    host=os.getenv("RABBITMQ_HOSTNAME"), # using container name as host instead of ip
    port=5672,
    username=rabbit_credentials['RABBITMQ_USER'],
    password=rabbit_credentials['RABBITMQ_PASSWORD']
).with_current_service(Service.DEVICES_MANAGER)

camera_repository = CameraRepositoryImpl(database_connector=database_connector)
reed_repository = ReedRepositoryImpl(database_connector=database_connector)
recording_repository = RecordingRepositoryImpl(database_connector=database_connector)
device_group_repository = DeviceGroupRepositoryImpl(database_connector=database_connector)

alarm_manager = AlarmManagerImpl(rabbitmq_client)
reeds_listener = ReedsListenerImpl(alarm_manager, reed_repository)
cameras_listener = CamerasListenerImpl(alarm_manager, camera_repository)
recording_manager = RecordingsManagerImpl(camera_repository, recording_repository)
device_group_service = DeviceGroupServiceImpl(device_group_repository, camera_repository, reed_repository, reeds_listener, alarm_manager)
reed_service = ReedServiceImpl(reed_repository=reed_repository, reeds_listener=reeds_listener, device_group_repository=device_group_repository)

camera_service = CameraServiceImpl(camera_repository=camera_repository, cameras_listener=cameras_listener, device_group_repository=device_group_repository)
recording_service = RecordingServiceImpl(recording_repository=recording_repository, camera_repository=camera_repository, recording_manager=recording_manager)

alarm_manager.set_recording_service(recording_service)

# Put them in an interface -> instance dict so they will be used everytime a dependency is required
bindings[DatabaseConnector] = database_connector
bindings[RabbitMQClient] = rabbitmq_client

bindings[CameraRepository] = camera_repository
bindings[RecordingRepository] = recording_repository
bindings[DeviceGroupRepository] = device_group_repository
bindings[ReedRepository] = reed_repository

bindings[CamerasListener] = cameras_listener
bindings[RecordingsManager] = recording_manager
bindings[AlarmManager] = alarm_manager
bindings[ReedsListener] = reeds_listener

bindings[CameraService] = camera_service
bindings[RecordingService] = recording_service
bindings[DeviceGroupService] = device_group_service
bindings[ReedService] = reed_service


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