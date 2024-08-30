from abc import ABC, abstractmethod

from app.database.database_connector import DatabaseConnector
from app.models.config.gpio_config import GpioConfig

class GpioConfigRepository(ABC):
    @abstractmethod
    def __init__(self, connector: DatabaseConnector):
        pass

    @abstractmethod
    def get_gpio_config(self, gpio_config_id: int) -> GpioConfig:
        pass

    @abstractmethod
    def create_gpio_config(self, gpio_config_id: int, value: int) -> GpioConfig:
        pass

    @abstractmethod
    def update_gpio_config(self, gpio_config_id: int, value: int) -> GpioConfig:
        pass

    @abstractmethod
    def delete_gpio_config(self, gpio_config_id: int) -> GpioConfig:
        pass
