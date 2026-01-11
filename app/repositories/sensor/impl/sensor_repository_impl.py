from typing import Sequence
from sqlmodel import select, and_

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.sensor import Sensor
from app.repositories.sensor.sensor_repository import SensorRepository


class SensorRepositoryImpl(SensorRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector

    def find_by_id(self, sensor_id: str) -> Sensor:
        statement = select(Sensor).where(Sensor.id == sensor_id)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        session.close()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")
        return sensor_db

    def find_by_server_and_pin(self, server_url: str, gpio_pin_number: int) -> Sensor:
        statement = select(Sensor).where(
            and_(
                Sensor.gpio_server_url == server_url,
                Sensor.gpio_pin_number == gpio_pin_number
            )
        )
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        session.close()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")
        return sensor_db

    def create(self, sensor: Sensor) -> Sensor:
        # Check if sensor with same server_url and pin already exists
        if self.exists_by_server_and_pin(sensor.gpio_server_url, sensor.gpio_pin_number):
            raise BadRequestException(
                f"Sensor with pin {sensor.gpio_pin_number} on server {sensor.gpio_server_url} already exists"
            )

        session = self.database_connector.get_new_session()
        session.add(sensor)
        session.commit()
        session.refresh(sensor)
        session.close()
        return sensor

    def update(self, sensor: Sensor) -> Sensor:
        statement = select(Sensor).where(Sensor.id == sensor.id)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")

        sensor_db.name = sensor.name
        # Note: gpio_pin_number and gpio_server_url should not be updated
        session.commit()
        session.refresh(sensor_db)
        session.close()
        return sensor_db

    def delete_by_id(self, sensor_id: str) -> Sensor:
        statement = select(Sensor).where(Sensor.id == sensor_id)
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
        statement = select(Sensor).where(Sensor.id == sensor.id)
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        if sensor_db is None:
            raise NotFoundException("Sensor was not found")

        sensor_db.listening = listening
        session.commit()
        session.refresh(sensor_db)
        session.close()
        return sensor_db

    def exists_by_server_and_pin(self, server_url: str, gpio_pin_number: int) -> bool:
        statement = select(Sensor).where(
            and_(
                Sensor.gpio_server_url == server_url,
                Sensor.gpio_pin_number == gpio_pin_number
            )
        )
        session = self.database_connector.get_new_session()
        sensor_db = session.exec(statement).first()
        session.close()
        return sensor_db is not None

    def update_listening_batch(self, sensors: Sequence[Sensor], listening: bool) -> None:
        if not sensors:
            return
        sensor_ids = [s.id for s in sensors]
        session = self.database_connector.get_new_session()
        statement = select(Sensor).where(Sensor.id.in_(sensor_ids))
        sensors_db = session.exec(statement).all()
        for sensor_db in sensors_db:
            sensor_db.listening = listening
        session.commit()
        session.close()