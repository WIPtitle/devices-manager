from app.database.database_connector import DatabaseConnector
from app.models.gpio_config import GpioConfig
from app.repositories.gpio_config.gpio_config_repository import GpioConfigRepository


class GpioConfigRepositoryImpl(GpioConfigRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector

    def get_gpio_config(self, gpio_config_id: int):
        return self.database_connector.get_db().query(GpioConfig).filter(GpioConfig.id == gpio_config_id).first()

    def create_gpio_config(self, gpio_config_id: int, value: int):
        db_gpio_config = GpioConfig(id=gpio_config_id, default_value_when_closed=value)
        self.database_connector.get_db().add(db_gpio_config)
        self.database_connector.get_db().commit()
        self.database_connector.get_db().refresh(db_gpio_config)
        return db_gpio_config

    def update_gpio_config(self, gpio_config_id: int, value: int):
        db_gpio_config = self.get_gpio_config(gpio_config_id)
        if db_gpio_config:
            db_gpio_config.value = value
            self.database_connector.get_db().commit()
            self.database_connector.get_db().refresh(db_gpio_config)
            return db_gpio_config
        return None

    def delete_gpio_config(self, gpio_config_id: int):
        db_gpio_config = self.get_gpio_config(gpio_config_id)
        if db_gpio_config:
            self.database_connector.get_db().delete(db_gpio_config)
            self.database_connector.get_db().commit()
            return db_gpio_config
        return None
