import os
from functools import wraps
from typing import Callable, get_type_hints

from rabbitmq_sdk.client.impl.rabbitmq_client_impl import RabbitMQClientImpl
from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.enums.service import Service

from app.database.database_connector import DatabaseConnector
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.jobs.impl.reeds_listener_impl import ReedsListenerImpl
from app.jobs.reeds_listener import ReedsListener
from app.repositories.reed.reed_repository import ReedRepository
from app.repositories.reed.impl.reed_repository_impl import ReedRepositoryImpl
from app.services.reed.reed_service import ReedService
from app.services.reed.impl.reed_service_impl import ReedServiceImpl
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
).with_current_service(Service.MAGNETIC_REEDS_LISTENER)

reeds_listener = ReedsListenerImpl()

reed_repository = ReedRepositoryImpl(database_connector=database_connector)
reed_service = ReedServiceImpl(reed_repository=reed_repository, reeds_listener=reeds_listener)

# Put them in an interface -> instance dict so they will be used everytime a dependency is required
bindings[DatabaseConnector] = database_connector
bindings[RabbitMQClient] = rabbitmq_client

bindings[ReedsListener] = reeds_listener

bindings[ReedRepository] = reed_repository
bindings[ReedService] = reed_service


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