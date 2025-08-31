import asyncio
from typing import Sequence, List

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.jobs.sensor.sensors_listener import SensorsListener
from app.models.sensor import Sensor
from app.repositories.sensor.sensor_repository import SensorRepository
from app.services.sensor.sensor_service import SensorService
from app.utils.event_manager import event_manager


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
                print(f"Warning: Could not add sensor {sensor.id}: {e}")

    def get_by_id(self, sensor_id: str) -> Sensor:
        return self.sensor_repository.find_by_id(sensor_id)

    def create(self, sensor: Sensor) -> Sensor:
        # First check if pin is monitored before creating
        self.sensors_listener.add_sensor(sensor)  # This will raise if not monitored
        sensor = self.sensor_repository.create(sensor)
        return sensor

    def update(self, sensor_id: str, sensor: Sensor) -> Sensor:
        if sensor.id != sensor_id:
            raise UnupdateableDataException("Can't update sensor id")

        # Don't allow updating gpio_pin_number or gpio_server_url
        existing = self.sensor_repository.find_by_id(sensor_id)
        if sensor.gpio_pin_number != existing.gpio_pin_number:
            raise UnupdateableDataException("Can't update gpio_pin_number")
        if sensor.gpio_server_url != existing.gpio_server_url:
            raise UnupdateableDataException("Can't update gpio_server_url")

        if sensor.listening:
            raise BadRequestException("Can't set listening here")

        if existing.listening:
            raise BadRequestException("Can't update while listening")

        sensor = self.sensor_repository.update(sensor)
        self.sensors_listener.update_sensor(sensor)
        return sensor

    def delete_by_id(self, sensor_id: str) -> Sensor:
        sensor = self.sensor_repository.find_by_id(sensor_id)
        if sensor.listening:
            raise BadRequestException("Can't delete while listening")

        sensor = self.sensor_repository.delete_by_id(sensor_id)
        self.sensors_listener.remove_sensor(sensor)
        return sensor

    def get_all(self) -> Sequence[Sensor]:
        return self.sensor_repository.find_all()

    def get_status_by_id(self, sensor_id: str) -> int:
        sensor = self.sensor_repository.find_by_id(sensor_id)
        return self.sensors_listener.get_status_by_sensor(sensor)

    async def get_sensor_status_stream_by_id(self, sensor_id: str):
        """Stream sensor status updates using events instead of polling"""
        # First, send the current status
        sensor = self.sensor_repository.find_by_id(sensor_id)
        current_status = self.sensors_listener.get_status_by_sensor(sensor)
        status_text = "HIGH" if current_status == 1 else "LOW"
        yield f"data: {status_text}\n\n"

        # Subscribe to events for this sensor (using sensor ID now)
        queue = await event_manager.subscribe_to_sensor(sensor_id)

        try:
            while True:
                try:
                    # Wait for events with a timeout to handle client disconnections
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    status_text = "HIGH" if event.data == 1 else "LOW"
                    yield f"data: {status_text}\n\n"
                except asyncio.TimeoutError:
                    # Send a keep-alive comment to prevent connection timeout
                    yield f": keep-alive\n\n"
        finally:
            # Clean up subscription when client disconnects
            await event_manager.unsubscribe_sensor(sensor_id, queue)
            print(f"Client disconnected from sensor {sensor_id} stream")

    def get_available_gpio_servers(self) -> List[str]:
        """Get list of available GPIO monitor servers"""
        return self.sensors_listener.get_available_servers()