import logging
from typing import Dict

from app.clients.gpio_monitor_client import GpioMonitorClient
from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.sensor.sensors_listener import SensorsListener
from app.models.sensor import Sensor
from app.repositories.sensor.sensor_repository import SensorRepository

logger = logging.getLogger(__name__)


class SensorsListenerImpl(SensorsListener):
    def __init__(self, alarm_manager: AlarmManager, sensor_repository: SensorRepository,
                 gpio_monitor_client: GpioMonitorClient):
        self.alarm_manager = alarm_manager
        self.sensor_repository = sensor_repository
        self.gpio_monitor_client = gpio_monitor_client
        self.sensor_states: Dict[int, int] = {}  # pin -> state (0=LOW, 1=HIGH)

        # Start the GPIO monitor client
        self.gpio_monitor_client.start()

        # Register callbacks for all existing sensors and initialize their states
        for sensor in self.sensor_repository.find_all():
            try:
                self._register_sensor_callback(sensor)
                self.sensor_states[sensor.gpio_pin_number] = self.gpio_monitor_client.get_pin_state(sensor.gpio_pin_number)
            except Exception as e:
                logger.error(f"Failed to initialize sensor on pin {sensor.gpio_pin_number}: {e}")

    def stop(self):
        """Stop the listener and cleanup"""
        self.gpio_monitor_client.stop()

    def add_sensor(self, sensor: Sensor):
        """Add a sensor to monitoring"""
        # Check if pin is being monitored by GPIO Monitor
        if not self.gpio_monitor_client.is_pin_monitored(sensor.gpio_pin_number):
            raise BadRequestException(f"Pin {sensor.gpio_pin_number} is not being monitored by GPIO Monitor")

        # Get initial state
        try:
            state = self.gpio_monitor_client.get_pin_state(sensor.gpio_pin_number)
            self.sensor_states[sensor.gpio_pin_number] = state
        except Exception as e:
            raise BadRequestException(f"Failed to get initial state for pin {sensor.gpio_pin_number}: {e}")

        # Register callback
        self._register_sensor_callback(sensor)

    def update_sensor(self, sensor: Sensor):
        """Update sensor (mainly for name changes)"""
        # Verify pin is still monitored
        if not self.gpio_monitor_client.is_pin_monitored(sensor.gpio_pin_number):
            raise BadRequestException(f"Pin {sensor.gpio_pin_number} is not being monitored by GPIO Monitor")

        # Update state
        try:
            state = self.gpio_monitor_client.get_pin_state(sensor.gpio_pin_number)
            self.sensor_states[sensor.gpio_pin_number] = state
        except Exception as e:
            raise BadRequestException(f"Failed to get state for pin {sensor.gpio_pin_number}: {e}")

    def remove_sensor(self, sensor: Sensor):
        """Remove a sensor from monitoring"""
        self.gpio_monitor_client.unregister_callback(sensor.gpio_pin_number)
        if sensor.gpio_pin_number in self.sensor_states:
            del self.sensor_states[sensor.gpio_pin_number]

    def get_status_by_sensor(self, sensor: Sensor) -> int:
        """Get current status of a sensor (0=LOW, 1=HIGH), cached if available"""
        if sensor.gpio_pin_number in self.sensor_states:
            return self.sensor_states[sensor.gpio_pin_number]

        try:
            state = self.gpio_monitor_client.get_pin_state(sensor.gpio_pin_number)
            self.sensor_states[sensor.gpio_pin_number] = state
            logger.warning(f"State for pin {sensor.gpio_pin_number} was not cached, fetched: {state}")
            return state
        except Exception as e:
            logger.error(f"Failed to get status for sensor on pin {sensor.gpio_pin_number}: {e}")
            raise BadRequestException(f"Failed to get sensor status: {e}")

    def _register_sensor_callback(self, sensor: Sensor):
        """Register a callback for sensor state changes"""

        def on_state_change(pin: int, state: int):
            # Update local state
            self.sensor_states[pin] = state

            # Only trigger alarm logic if sensor is listening and state is HIGH
            if state == 1:  # HIGH state
                try:
                    sensor_db = self.sensor_repository.find_by_gpio_pin_number(pin)
                    if sensor_db.listening:
                        logger.info(f"Sensor on pin {pin} triggered (state=HIGH)")
                        self.alarm_manager.on_sensor_triggered(pin)
                except Exception as e:
                    logger.error(f"Error handling state change for pin {pin}: {e}")

        self.gpio_monitor_client.register_callback(sensor.gpio_pin_number, on_state_change)