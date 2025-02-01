from typing import Sequence

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.jobs.pir.pirs_listener import PirsListener
from app.models.enums.pir_status import PirStatus
from app.models.pir import Pir
from app.repositories.pir.pir_repository import PirRepository
from app.services.pir.pir_service import PirService


class PirServiceImpl(PirService):
    def __init__(self, pir_repository: PirRepository, pirs_listener: PirsListener):
        self.pir_repository = pir_repository
        self.pirs_listener = pirs_listener

        # When service is created on app init, start listening to already saved pirs.
        for pir in self.pir_repository.find_all():
            self.pirs_listener.add_pir(pir)


    def get_by_pin(self, gpio_pin_number: int) -> Pir:
        return self.pir_repository.find_by_gpio_pin_number(gpio_pin_number)


    def create(self, pir: Pir) -> Pir:
        pir = self.pir_repository.create(pir)
        self.pirs_listener.add_pir(pir)
        return pir


    def update(self, gpio_pin_number: int, pir: Pir) -> Pir:
        if pir.gpio_pin_number != gpio_pin_number:
            raise UnupdateableDataException("Can't update gpio_pin_number")

        if pir.listening:
            raise BadRequestException("Can't set listening here")

        if self.pir_repository.find_by_gpio_pin_number(gpio_pin_number).listening:
            raise BadRequestException("Can't update while listening")

        pir = self.pir_repository.update(pir)
        self.pirs_listener.update_pir(pir)
        return pir


    def delete_by_pin(self, gpio_pin_number: int) -> Pir:
        if self.pir_repository.find_by_gpio_pin_number(gpio_pin_number).listening:
            raise BadRequestException("Can't delete while listening")

        pir = self.pir_repository.delete_by_gpio_pin_number(gpio_pin_number)
        self.pirs_listener.remove_pir(pir)
        return pir


    def get_all(self) -> Sequence[Pir]:
        return self.pir_repository.find_all()


    def get_status_by_pin(self, gpio_pin_number: int) -> PirStatus:
        pir = self.pir_repository.find_by_gpio_pin_number(gpio_pin_number)
        return self.pirs_listener.get_status_by_pir(pir)
