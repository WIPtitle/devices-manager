from abc import ABC, abstractmethod
from typing import Optional

from app.database.database_connector import DatabaseConnector
from app.models.reed import Reed


class ReedRepository(ABC):
    @abstractmethod
    def __init__(self, database_connector: DatabaseConnector):
        pass

    @abstractmethod
    def find_by_gpio_pin_number(self, gpio_pin_number: int) -> Optional[Reed]:
        pass

    @abstractmethod
    def create(self, reed: Reed) -> Reed:
        pass

    @abstractmethod
    def update(self, reed: Reed) -> Optional[Reed]:
        pass

    @abstractmethod
    def delete_by_gpio_pin_number(self, gpio_pin_number: int) -> Reed:
        pass
