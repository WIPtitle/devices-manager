from dependency_injector import containers, providers

import app as app_package
from app.database.database_connector import DatabaseConnector
from app.database.impl.database_connector_impl import DatabaseConnectorImpl
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository
from app.repositories.gpio_config.impl.gpio_config_repository_impl import GpioConfigRepositoryImpl
from app.services.gpio_config.gpio_config_service import GpioConfigService
from app.services.gpio_config.impl.gpio_config_service_impl import GpioConfigServiceImpl
from app.utils.modules_discover import discover_all_modules


class Bindings(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=discover_all_modules(app_package)
    )

    database_connector_instance = providers.Singleton(DatabaseConnectorImpl)

    gpio_config_repository_instance = providers.Singleton(GpioConfigRepositoryImpl, database_connector=database_connector_instance)
    gpio_config_service_instance = providers.Singleton(GpioConfigServiceImpl, gpio_config_repository=gpio_config_repository_instance)

    database_connection_interface = providers.Singleton(DatabaseConnector, provided=database_connector_instance)
    gpio_config_repository_interface = providers.Singleton(GpioConfigRepository, provided=gpio_config_repository_instance)
    gpio_config_service_interface = providers.Singleton(GpioConfigService, provided=gpio_config_service_instance)

