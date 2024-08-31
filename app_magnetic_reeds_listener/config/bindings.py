from functools import wraps
from typing import Callable, get_type_hints

from app_magnetic_reeds_listener.database.database_connector import DatabaseConnector
from app_magnetic_reeds_listener.database.impl.database_connector_impl import DatabaseConnectorImpl
from app_magnetic_reeds_listener.repositories.gpio_config.gpio_config_repository import GpioConfigRepository
from app_magnetic_reeds_listener.repositories.gpio_config.impl.gpio_config_repository_impl import GpioConfigRepositoryImpl
from app_magnetic_reeds_listener.services.gpio_config.gpio_config_service import GpioConfigService
from app_magnetic_reeds_listener.services.gpio_config.impl.gpio_config_service_impl import GpioConfigServiceImpl

bindings = { }

# Create instances only one time
database_connector = DatabaseConnectorImpl()
gpio_config_repository = GpioConfigRepositoryImpl(database_connector=database_connector)
gpio_config_service = GpioConfigServiceImpl(gpio_config_repository=gpio_config_repository)

# Put them in an interface -> instance dict so they will be used everytime a dependency is required
bindings[DatabaseConnector] = database_connector
bindings[GpioConfigRepository] = gpio_config_repository
bindings[GpioConfigService] = gpio_config_service


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