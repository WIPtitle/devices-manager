from typing import Sequence

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.jobs.reed.reeds_listener import ReedsListener
from app.models.device_group import Device
from app.models.enums.device_type import DeviceType
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.reed.reed_repository import ReedRepository
from app.services.reed.reed_service import ReedService


class ReedServiceImpl(ReedService):
    def __init__(self, reed_repository: ReedRepository, reeds_listener: ReedsListener, device_group_repository: DeviceGroupRepository):
        self.reed_repository = reed_repository
        self.reeds_listener = reeds_listener
        self.device_group_repository = device_group_repository

        # When service is created on app init, start listening to already saved reeds.
        for reed in self.reed_repository.find_all():
            self.reeds_listener.add_reed(reed)


    def get_by_pin(self, gpio_pin_number: int) -> Reed:
        return self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)


    def get_by_generic_device_id(self, device_id: int) -> Reed:
        return self.reed_repository.find_by_generic_device_id(device_id)


    def create(self, reed: Reed) -> Reed:
        reed = self.reed_repository.create(reed)
        device = self.device_group_repository.create_device(Device(device_type=DeviceType.MAGNETIC_REED))
        reed.generic_device_id = device.id
        self.reeds_listener.add_reed(reed)
        return reed


    def update(self, gpio_pin_number: int, reed: Reed) -> Reed:
        if reed.gpio_pin_number != gpio_pin_number:
            raise UnupdateableDataException("Can't update gpio_pin_number")

        if reed.listening:
            raise BadRequestException("Can't set listening here")

        if self.reed_repository.find_by_gpio_pin_number(gpio_pin_number).listening:
            raise BadRequestException("Can't update while listening")

        reed = self.reed_repository.update(reed)
        self.reeds_listener.update_reed(reed)
        return reed


    def delete_by_pin(self, gpio_pin_number: int) -> Reed:
        if self.reed_repository.find_by_gpio_pin_number(gpio_pin_number).listening:
            raise BadRequestException("Can't delete while listening")

        reed = self.reed_repository.delete_by_gpio_pin_number(gpio_pin_number)
        to_delete = self.device_group_repository.delete_device_group(reed.generic_device.id)
        self.device_group_repository.delete_device(to_delete.id)
        self.reeds_listener.remove_reed(reed)
        return reed


    def get_all(self) -> Sequence[Reed]:
        return self.reed_repository.find_all()


    def get_status_by_pin(self, gpio_pin_number: int) -> ReedStatus:
        reed = self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)
        return self.reeds_listener.get_status_by_reed(reed)
