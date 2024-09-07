from typing import Sequence

from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.jobs.reeds_listener import ReedsListener
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository
from app.services.reed.reed_service import ReedService


class ReedServiceImpl(ReedService):
    def __init__(self, reed_repository: ReedRepository, reeds_listener: ReedsListener):
        self.reed_repository = reed_repository
        self.reeds_listener = reeds_listener

        # When service is created on app init, start listening to already saved reeds.
        for reed in self.reed_repository.find_all():
            self.reeds_listener.add_reed(reed)


    def get_by_pin(self, gpio_pin_number: int) -> Reed:
        return self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)


    def create(self, reed: Reed) -> Reed:
        reed = self.reed_repository.create(reed)
        self.reeds_listener.add_reed(reed)
        return reed


    def update(self, gpio_pin_number: int, reed: Reed) -> Reed:
        if reed.gpio_pin_number != gpio_pin_number:
            raise UnupdateableDataException("Can't update gpio_pin_number")

        reed = self.reed_repository.update(reed)
        self.reeds_listener.update_reed(reed)
        return reed


    def delete_by_pin(self, gpio_pin_number: int) -> Reed:
        reed = self.reed_repository.delete_by_gpio_pin_number(gpio_pin_number)
        self.reeds_listener.remove_reed(reed)
        return reed


    def get_all(self) -> Sequence[Reed]:
        return self.reed_repository.find_all()


    def get_status_by_pin(self, gpio_pin_number: int) -> ReedStatus:
        reed = self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)
        return self.reeds_listener.get_status_by_reed(reed)
