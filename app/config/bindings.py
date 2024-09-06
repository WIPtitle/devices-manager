import os
from functools import wraps
from typing import Callable, get_type_hints

from rabbitmq_sdk.client.impl.rabbitmq_client_impl import RabbitMQClientImpl
from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.enums.service import Service

from app.database.database_connector import DatabaseConnector
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.jobs.impl.cameras_listener_impl import CamerasListenerImpl
from app.jobs.cameras_listener import CamerasListener
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.camera.impl.camera_repository_impl import CameraRepositoryImpl
from app.services.camera.camera_service_impl import CameraService
from app.services.camera.impl.camera_service_impl import CameraServiceImpl
from app.utils.read_credentials import read_credentials

bindings = { }

# Create instances only one time
database_connector = DatabaseConnectorImpl()

rabbit_credentials = read_credentials(os.getenv('RBBT_CREDENTIALS_FILE'))
rabbitmq_client = RabbitMQClientImpl.from_config(
    host='rabbitmq', # using container name as host instead of ip
    port=5672,
    username=rabbit_credentials['RABBITMQ_USER'],
    password=rabbit_credentials['RABBITMQ_PASSWORD']
).with_current_service(Service.RTSP_CAMERAS_LISTENER)

cameras_listener = CamerasListenerImpl(rabbitmq_client)

camera_repository = CameraRepositoryImpl(database_connector=database_connector)
camera_service = CameraServiceImpl(camera_repository=camera_repository, cameras_listener=cameras_listener)

# Put them in an interface -> instance dict so they will be used everytime a dependency is required
bindings[DatabaseConnector] = database_connector
bindings[RabbitMQClient] = rabbitmq_client

bindings[CamerasListener] = cameras_listener

bindings[CameraRepository] = camera_repository
bindings[CameraService] = camera_service


def resolve(interface):
    implementation = bindings[interface]
    if implementation is None:
        raise ValueError(f"No binding found for {interface}")
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