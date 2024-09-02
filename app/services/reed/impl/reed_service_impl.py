from typing import Optional

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.magnetic_reeds_listener.enums.status import Status
from rabbitmq_sdk.event.impl.magnetic_reeds_listener.reed_changed_value import ReedChangedValue

from app.exceptions.not_found_exception import NotFoundException
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository
from app.services.reed.reed_service import ReedService
from app.config.bindings import inject


class ReedServiceImpl(ReedService):
    @inject
    def __init__(self, reed_repository: ReedRepository, rabbitmq_client: RabbitMQClient):
        self.reed_repository = reed_repository
        self.rabbitmq_client = rabbitmq_client

    def get_by_id(self, gpio_pin_number: int) -> Reed:
        self.rabbitmq_client.publish(ReedChangedValue(1, Status.OPEN)) #TODO remove after testing obviously
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
