from typing import Optional

from sqlmodel import select

from app_magnetic_reeds_listener.database.database_connector import DatabaseConnector
from app_magnetic_reeds_listener.models.gpio_config import GpioConfig
from app_magnetic_reeds_listener.repositories.gpio_config.gpio_config_repository import GpioConfigRepository


class GpioConfigRepositoryImpl(GpioConfigRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector

    def find_by_id(self, gpio_config_id: int) -> Optional[GpioConfig]:
        statement = select(GpioConfig).where(GpioConfig.id == gpio_config_id)
        return self.database_connector.get_session().exec(statement).first()

    def create(self, gpio_config: GpioConfig) -> GpioConfig:
        self.database_connector.get_session().add(gpio_config)
        self.database_connector.get_session().commit()
        self.database_connector.get_session().refresh(gpio_config)
        return gpio_config

    def update(self, gpio_config: GpioConfig) -> Optional[GpioConfig]:
        gpio_config_db = self.find_by_id(gpio_config.id)
        if gpio_config_db:
            gpio_config_db.default_value_when_closed = gpio_config.default_value_when_closed
            self.database_connector.get_session().commit()
            self.database_connector.get_session().refresh(gpio_config_db)
        return gpio_config_db

    def delete_by_id(self, gpio_config_id: int):
        gpio_config = self.find_by_id(gpio_config_id)
        if gpio_config:
            self.database_connector.get_session().delete(gpio_config)
            self.database_connector.get_session().commit()
        return gpio_config
