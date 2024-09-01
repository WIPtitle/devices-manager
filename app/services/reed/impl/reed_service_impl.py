from typing import Optional

from app.exceptions.not_found_exception import NotFoundException
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository
from app.services.reed.reed_service import ReedService


class ReedServiceImpl(ReedService):
    def __init__(self, reed_repository: ReedRepository):
        self.reed_repository = reed_repository

    def get_by_id(self, gpio_pin_number: int) -> Reed:
        reed: Optional[Reed] = self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)
        if reed is None:
            raise NotFoundException("Gpio config was not found")
        return reed

    def create(self, reed: Reed) -> Reed:
        return self.reed_repository.create(reed)

    def update(self, reed: Reed) -> Reed:
        reed = self.reed_repository.update(reed)
        if reed is None:
            raise NotFoundException("Gpio config was not found")
        return reed

    def delete_by_id(self, gpio_pin_number: int) -> Reed:
        return self.reed_repository.delete_by_gpio_pin_number(gpio_pin_number)
