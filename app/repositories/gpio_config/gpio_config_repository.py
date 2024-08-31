from abc import ABC, abstractmethod
from typing import Optional

from app.database.database_connector import DatabaseConnector
from app.models.gpio_config import GpioConfig


class GpioConfigRepository(ABC):
    @abstractmethod
    def __init__(self, database_connector: DatabaseConnector):
        pass

    @abstractmethod
    def find_by_id(self, gpio_config_id: int) -> Optional[GpioConfig]:
        pass

    @abstractmethod
    def create(self, gpio_config: GpioConfig) -> GpioConfig:
        pass

    @abstractmethod
    def update(self, gpio_config: GpioConfig) -> Optional[GpioConfig]:
        pass

    @abstractmethod
    def delete_by_id(self, gpio_config_id: int) -> GpioConfig:
        pass
