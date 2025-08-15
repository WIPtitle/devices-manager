from typing import Sequence
from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.sensor import Sensor
from app.repositories.sensor.sensor_repository import SensorRepository


class SensorRepositoryImpl(SensorRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector

    def find_by_gpio_pin_number(self, gpio_pin_number: int) -> Sensor:
        statement = select(Sensor).where(Sensor.gpio_pin_number == gpio_pin_number)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        session.close()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")
        return sensor_db

    def create(self, sensor: Sensor) -> Sensor:
        try:
            self.find_by_gpio_pin_number(sensor.gpio_pin_number)
        except NotFoundException:
            session = self.database_connector.get_new_session()
            session.add(sensor)
            session.commit()
            session.refresh(sensor)
            session.close()
            return sensor
        raise BadRequestException("Sensor already exists")

    def update(self, sensor: Sensor) -> Sensor:
        statement = select(Sensor).where(Sensor.gpio_pin_number == sensor.gpio_pin_number)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")

        sensor_db.name = sensor.name
        session.commit()
        session.refresh(sensor_db)
        session.close()
        return sensor_db

    def delete_by_gpio_pin_number(self, gpio_pin_number: int) -> Sensor:
        statement = select(Sensor).where(Sensor.gpio_pin_number == gpio_pin_number)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")

        session.delete(sensor_db)
        session.commit()
        session.close()
        return sensor_db

    def find_all(self) -> Sequence[Sensor]:
        statement = select(Sensor)
        session = self.database_connector.get_new_session()
        result = session.exec(statement).all()
        session.close()
        return result

    def update_listening(self, sensor: Sensor, listening: bool) -> Sensor:
        statement = select(Sensor).where(Sensor.gpio_pin_number == sensor.gpio_pin_number)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")

        sensor_db.listening = listening
        session.commit()
        session.refresh(sensor_db)
        session.close()
        return sensor_db