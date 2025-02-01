from abc import ABC, abstractmethod
from typing import Sequence

from app.models.pir import Pir


class PirRepository(ABC):
    @abstractmethod
    def find_by_gpio_pin_number(self, gpio_pin_number: int) -> Pir:
        pass

    @abstractmethod
    def create(self, pir: Pir) -> Pir:
        pass

    @abstractmethod
    def update(self, pir: Pir) -> Pir:
        pass

    @abstractmethod
    def delete_by_gpio_pin_number(self, gpio_pin_number: int) -> Pir:
        pass

    @abstractmethod
    def find_all(self) -> Sequence[Pir]:
        pass

    @abstractmethod
    def update_listening(self, pir: Pir, listening: bool):
        pass
