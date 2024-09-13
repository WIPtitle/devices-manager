from abc import ABC, abstractmethod
from typing import Sequence

from app.models.reed import Reed


class ReedRepository(ABC):
    @abstractmethod
    def find_by_gpio_pin_number(self, gpio_pin_number: int) -> Reed:
        pass

    @abstractmethod
    def find_by_generic_device_id(self, device_id: int):
        pass

    @abstractmethod
    def create(self, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def update(self, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def delete_by_gpio_pin_number(self, gpio_pin_number: int) -> Reed:
        pass

    @abstractmethod
    def find_all(self) -> Sequence[Reed]:
        pass

    @abstractmethod
    def update_listening(self, reed: Reed, listening: bool):
        pass
