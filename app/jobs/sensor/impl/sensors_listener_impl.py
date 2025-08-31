from typing import Dict, List, Tuple

from app.clients.gpio_monitor_client import GpioMonitorClient
from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.sensor.sensors_listener import SensorsListener
from app.models.sensor import Sensor
from app.repositories.sensor.sensor_repository import SensorRepository
from app.utils.event_manager import event_manager


class SensorsListenerImpl(SensorsListener):
    def __init__(self, alarm_manager: AlarmManager, sensor_repository: SensorRepository,
                 gpio_monitor_clients: List[Tuple[str, GpioMonitorClient]]):
        """
        Initialize with multiple GPIO monitor clients
        gpio_monitor_clients: List of tuples (server_url, client_instance)
        """
        self.alarm_manager = alarm_manager
        self.sensor_repository = sensor_repository
        # Dictionary mapping server_url to client instance
        self.gpio_clients: Dict[str, GpioMonitorClient] = dict(gpio_monitor_clients)
        # sensor_states: (server_url, pin) -> state (0=LOW, 1=HIGH)
        self.sensor_states: Dict[Tuple[str, int], int] = {}

        # Start all GPIO monitor clients
        for server_url, client in self.gpio_clients.items():
            client.start()
            print(f"Started GPIO monitor client for {server_url}")

        # Register callbacks for all existing sensors and initialize their states
        for sensor in self.sensor_repository.find_all():
            try:
                self._register_sensor_callback(sensor)
                client = self.gpio_clients.get(sensor.gpio_server_url)
                if client:
                    initial_state = client.get_pin_state(sensor.gpio_pin_number)
                    self.sensor_states[(sensor.gpio_server_url, sensor.gpio_pin_number)] = initial_state
                    # Publish initial state using sensor ID
                    event_manager.publish_sensor_event_sync(sensor.id, initial_state)
                else:
                    print(f"No client found for server {sensor.gpio_server_url}")
            except Exception as e:
                print(f"Failed to initialize sensor {sensor.id} on pin {sensor.gpio_pin_number} "
                      f"at {sensor.gpio_server_url}: {e}")

    def stop(self):
        """Stop all listeners and cleanup"""
        for server_url, client in self.gpio_clients.items():
            client.stop()
            print(f"Stopped GPIO monitor client for {server_url}")

    def add_sensor(self, sensor: Sensor):
        """Add a sensor to monitoring"""
        # Get the appropriate client for this sensor's server
        client = self.gpio_clients.get(sensor.gpio_server_url)
        if not client:
            raise BadRequestException(
                f"No GPIO Monitor client configured for server {sensor.gpio_server_url}"
            )

        # Check if pin is being monitored by the specific GPIO Monitor server
        if not client.is_pin_monitored(sensor.gpio_pin_number):
            raise BadRequestException(
                f"Pin {sensor.gpio_pin_number} is not being monitored by GPIO Monitor at {sensor.gpio_server_url}"
            )

        # Get initial state
        try:
            state = client.get_pin_state(sensor.gpio_pin_number)
            self.sensor_states[(sensor.gpio_server_url, sensor.gpio_pin_number)] = state
            # Publish initial state for new sensor using sensor ID
            event_manager.publish_sensor_event_sync(sensor.id, state)
        except Exception as e:
            raise BadRequestException(
                f"Failed to get initial state for pin {sensor.gpio_pin_number} at {sensor.gpio_server_url}: {e}"
            )

        # Register callback
        self._register_sensor_callback(sensor)

    def update_sensor(self, sensor: Sensor):
        """Update sensor (mainly for name changes)"""
        # Get the appropriate client
        client = self.gpio_clients.get(sensor.gpio_server_url)
        if not client:
            raise BadRequestException(
                f"No GPIO Monitor client configured for server {sensor.gpio_server_url}"
            )

        # Verify pin is still monitored
        if not client.is_pin_monitored(sensor.gpio_pin_number):
            raise BadRequestException(
                f"Pin {sensor.gpio_pin_number} is not being monitored by GPIO Monitor at {sensor.gpio_server_url}"
            )

        # Update state
        try:
            state = client.get_pin_state(sensor.gpio_pin_number)
            key = (sensor.gpio_server_url, sensor.gpio_pin_number)
            old_state = self.sensor_states.get(key)
            self.sensor_states[key] = state

            # Publish event if state changed (using sensor ID)
            if old_state != state:
                event_manager.publish_sensor_event_sync(sensor.id, state)
        except Exception as e:
            raise BadRequestException(
                f"Failed to get state for pin {sensor.gpio_pin_number} at {sensor.gpio_server_url}: {e}"
            )

    def remove_sensor(self, sensor: Sensor):
        """Remove a sensor from monitoring"""
        client = self.gpio_clients.get(sensor.gpio_server_url)
        if client:
            client.unregister_callback(sensor.gpio_pin_number)

        key = (sensor.gpio_server_url, sensor.gpio_pin_number)
        if key in self.sensor_states:
            del self.sensor_states[key]

    def get_status_by_sensor(self, sensor: Sensor) -> int:
        """Get current status of a sensor (0=LOW, 1=HIGH), cached if available"""
        key = (sensor.gpio_server_url, sensor.gpio_pin_number)
        if key in self.sensor_states:
            return self.sensor_states[key]

        client = self.gpio_clients.get(sensor.gpio_server_url)
        if not client:
            raise BadRequestException(
                f"No GPIO Monitor client configured for server {sensor.gpio_server_url}"
            )

        try:
            state = client.get_pin_state(sensor.gpio_pin_number)
            self.sensor_states[key] = state
            print(f"State for sensor {sensor.id} was not cached, fetched: {state}")
            # Publish the newly fetched state using sensor ID
            event_manager.publish_sensor_event_sync(sensor.id, state)
            return state
        except Exception as e:
            print(f"Failed to get status for sensor {sensor.id}: {e}")
            raise BadRequestException(f"Failed to get sensor status: {e}")

    def get_available_servers(self) -> List[str]:
        """Get list of available GPIO monitor servers"""
        return list(self.gpio_clients.keys())

    def _register_sensor_callback(self, sensor: Sensor):
        """Register a callback for sensor state changes"""
        client = self.gpio_clients.get(sensor.gpio_server_url)
        if not client:
            print(f"No client found for server {sensor.gpio_server_url}, skipping callback registration")
            return

        def on_state_change(pin: int, state: int):
            key = (sensor.gpio_server_url, pin)
            old_state = self.sensor_states.get(key)
            # Update local state
            self.sensor_states[key] = state

            # Publish event if state actually changed (using sensor ID)
            if old_state != state:
                print(
                    f"Sensor {sensor.id} on pin {pin} at {sensor.gpio_server_url} state changed from {old_state} to {state}")
                event_manager.publish_sensor_event_sync(sensor.id, state)

            # Only trigger alarm logic if sensor is listening and state is HIGH
            if state == 1:  # HIGH state
                try:
                    # Find sensor by server_url and pin combination
                    sensor_db = self.sensor_repository.find_by_server_and_pin(sensor.gpio_server_url, pin)
                    if sensor_db.listening:
                        print(f"Sensor {sensor_db.id} triggered (state=HIGH)")
                        self.alarm_manager.on_sensor_triggered(sensor_db.id)
                except Exception as e:
                    print(f"Error handling state change for pin {pin} at {sensor.gpio_server_url}: {e}")

        client.register_callback(sensor.gpio_pin_number, on_state_change)