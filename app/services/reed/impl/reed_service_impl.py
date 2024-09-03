from typing import Optional, Sequence

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.internal_error_exception import InternalErrorException
from app.exceptions.not_found_exception import NotFoundException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository
from app.services.reed.reed_service import ReedService


class ReedServiceImpl(ReedService):
    def __init__(self, reed_repository: ReedRepository):
        self.reed_repository = reed_repository


    def get_by_id(self, gpio_pin_number: int) -> Reed:
        reed: Optional[Reed] = self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)
        if reed is None:
            raise NotFoundException("Reed was not found")
        return reed


    def create(self, reed: Reed) -> Reed:
        db_reed = self.reed_repository.find_by_gpio_pin_number(reed.gpio_pin_number)
        if db_reed is not None:
            raise BadRequestException("Reed already exists")
        return self.reed_repository.create(reed)


    def update(self, gpio_pin_number: int, reed: Reed) -> Reed:
        reed = self.reed_repository.find_by_gpio_pin_number(gpio_pin_number)
        if reed is None:
            raise NotFoundException("Reed was not found")

        if reed.gpio_pin_number is not gpio_pin_number:
            raise UnupdateableDataException("Can't update gpio_pin_number")

        reed = self.reed_repository.update(reed)
        if reed is None:
            raise InternalErrorException("Gpio config can't be updated")
        return reed


    def delete_by_id(self, gpio_pin_number: int) -> Reed:
        return self.reed_repository.delete_by_gpio_pin_number(gpio_pin_number)


    def get_all(self) -> Sequence[Reed]:
        return self.reed_repository.find_all()


    def get_status_by_id(self, gpio_pin_number: int) -> ReedStatus:
        # TODO this will be fun
        return ReedStatus.CLOSED


