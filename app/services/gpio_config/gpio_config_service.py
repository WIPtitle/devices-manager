from abc import ABC, abstractmethod
from app.models.gpio_config import GpioConfig
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository


class GpioConfigService(ABC):
    @abstractmethod
    def __init__(self, gpio_config_repository: GpioConfigRepository):
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
