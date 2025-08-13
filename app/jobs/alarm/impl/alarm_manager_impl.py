import time
from collections import deque
from threading import Lock

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.base_event import BaseEvent
from rabbitmq_sdk.event.impl.devices_manager.alarm_stopped import AlarmStopped
from rabbitmq_sdk.event.impl.devices_manager.sensor_alarm import SensorAlarm
from rabbitmq_sdk.event.impl.devices_manager.alarm_waiting import AlarmWaiting

from app.jobs.alarm.alarm_manager import AlarmManager
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.recording import Recording, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.sensor.sensor_repository import SensorRepository
from app.services.recording.recording_service import RecordingService
from app.utils.delayed_execution import delay_execution


class AlarmManagerImpl(AlarmManager):
    def __init__(self,
                 rabbitmq_client: RabbitMQClient,
                 recording_service: RecordingService,
                 device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 sensor_repository: SensorRepository):
        self.rabbitmq_client = rabbitmq_client
        self.recording_service = recording_service
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.sensor_repository = sensor_repository
        self.alarm = False

        # Trigger filtering attributes
        self.trigger_timestamps = deque()
        self.trigger_lock = Lock()
        self.window_duration = 5.0
        self.min_triggers = 3

    def _clean_old_triggers(self, current_time: float):
        """Remove trigger timestamps older than the window duration"""
        cutoff_time = current_time - self.window_duration
        while self.trigger_timestamps and self.trigger_timestamps[0] < cutoff_time:
            self.trigger_timestamps.popleft()

    def _is_there_enough_triggers_in_window(self, current_time: float) -> bool:
        """Check if we have enough triggers in the time window to trigger alarm"""
        with self.trigger_lock:
            self._clean_old_triggers(current_time)
            return len(self.trigger_timestamps) >= self.min_triggers

    def on_sensor_triggered(self, sensor_pin: int):
        """Called when any sensor is triggered (goes HIGH)"""
        sensor = self.sensor_repository.find_by_gpio_pin_number(sensor_pin)
        group = self.device_group_repository.find_listening_device_group()
        current_time = time.time()

        with self.trigger_lock:
            # Add current trigger timestamp
            self.trigger_timestamps.append(current_time)
            self._clean_old_triggers(current_time)

            # Check if we should trigger the alarm
            if not self.alarm and self._is_there_enough_triggers_in_window(current_time):
                self.alarm = True
                while not self.rabbitmq_client.publish(AlarmWaiting(True, int(current_time))):
                    time.sleep(1)
                delay_execution(
                    func=self.trigger_alarm,
                    args=(SensorAlarm(sensor.name, int(current_time)), group.id),
                    delay_seconds=group.wait_to_fire_alarm)

    def trigger_alarm(self, event: BaseEvent, group_id: int):
        """Trigger the alarm after the delay"""
        # Find listening group and set it to alarm
        group = self.device_group_repository.find_device_group_by_id(group_id)

        # Check if still listening
        if group.status != DeviceGroupStatus.LISTENING:
            return

        group.status = DeviceGroupStatus.ALARM
        self.device_group_repository.update_device_group(group)

        while not self.rabbitmq_client.publish(AlarmWaiting(False, int(time.time()))):
            time.sleep(1)

        # After two minutes, stop audio and recordings
        delay_execution(
            func=self.stop_alarm,
            delay_seconds=120)

        while not self.rabbitmq_client.publish(event):
            time.sleep(1)

        # Start recording for cameras that are not always recording
        for camera in self.camera_repository.find_all():
            if not camera.always_recording:
                self.recording_service.create_and_start_recording(
                    Recording.from_dto(RecordingInputDto(camera_ip=camera.ip, always_recording=False)),
                    auto_restart=False)

    def stop_alarm(self):
        """Stop the alarm"""
        if self.alarm:
            while not self.rabbitmq_client.publish(AlarmStopped(int(time.time()))):
                time.sleep(1)

            for camera in self.camera_repository.find_all():
                if not camera.always_recording:
                    self.recording_service.stop_by_camera_ip(camera.ip)
            self.alarm = False