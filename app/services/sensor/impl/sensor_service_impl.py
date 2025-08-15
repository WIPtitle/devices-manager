import asyncio
from typing import Sequence

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.jobs.sensor.sensors_listener import SensorsListener
from app.models.sensor import Sensor
from app.repositories.sensor.sensor_repository import SensorRepository
from app.services.sensor.sensor_service import SensorService


class SensorServiceImpl(SensorService):
    def __init__(self, sensor_repository: SensorRepository, sensors_listener: SensorsListener):
        self.sensor_repository = sensor_repository
        self.sensors_listener = sensors_listener

        # When service is created on app init, start listening to already saved sensors
        for sensor in self.sensor_repository.find_all():
            try:
                self.sensors_listener.add_sensor(sensor)
            except Exception as e:
                # Log but don't fail startup if a sensor is no longer monitored
                print(f"Warning: Could not add sensor on pin {sensor.gpio_pin_number}: {e}")

    def get_by_pin(self, gpio_pin_number: int) -> Sensor:
        return self.sensor_repository.find_by_gpio_pin_number(gpio_pin_number)

    def create(self, sensor: Sensor) -> Sensor:
        # First check if pin is monitored before creating
        self.sensors_listener.add_sensor(sensor)  # This will raise if not monitored
        sensor = self.sensor_repository.create(sensor)
        return sensor

    def update(self, gpio_pin_number: int, sensor: Sensor) -> Sensor:
        if sensor.gpio_pin_number != gpio_pin_number:
            raise UnupdateableDataException("Can't update gpio_pin_number")

        if sensor.listening:
            raise BadRequestException("Can't set listening here")

        if self.sensor_repository.find_by_gpio_pin_number(gpio_pin_number).listening:
            raise BadRequestException("Can't update while listening")

        sensor = self.sensor_repository.update(sensor)
        self.sensors_listener.update_sensor(sensor)
        return sensor

    def delete_by_pin(self, gpio_pin_number: int) -> Sensor:
        if self.sensor_repository.find_by_gpio_pin_number(gpio_pin_number).listening:
            raise BadRequestException("Can't delete while listening")

        sensor = self.sensor_repository.delete_by_gpio_pin_number(gpio_pin_number)
        self.sensors_listener.remove_sensor(sensor)
        return sensor

    def get_all(self) -> Sequence[Sensor]:
        return self.sensor_repository.find_all()

    def get_status_by_pin(self, gpio_pin_number: int) -> int:
        sensor = self.sensor_repository.find_by_gpio_pin_number(gpio_pin_number)
        return self.sensors_listener.get_status_by_sensor(sensor)

    async def get_sensor_status_stream_by_pin(self, gpio_pin_number: int):
        """Stream sensor status updates"""
        while True:
            await asyncio.sleep(1)
            sensor = self.sensor_repository.find_by_gpio_pin_number(gpio_pin_number)
            status = self.sensors_listener.get_status_by_sensor(sensor)
            status_text = "HIGH" if status == 1 else "LOW"
            yield f"data: {status_text}\n\n"