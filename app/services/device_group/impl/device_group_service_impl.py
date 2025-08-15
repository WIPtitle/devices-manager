import asyncio
import time
from typing import Sequence

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.devices_manager.alarm_waiting import AlarmWaiting

from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.models.device_group import DeviceGroup
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.sensor import Sensor
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.sensor.sensor_repository import SensorRepository
from app.services.device_group.device_group_service import DeviceGroupService
from app.utils.delayed_execution import delay_execution
from app.utils.event_manager import event_manager


class DeviceGroupServiceImpl(DeviceGroupService):
    def __init__(self,
                 device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 sensor_repository: SensorRepository,
                 alarm_manager: AlarmManager,
                 rabbitmq_client: RabbitMQClient):
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.sensor_repository = sensor_repository
        self.alarm_manager = alarm_manager
        self.rabbitmq_client = rabbitmq_client

        # Publish initial state for all existing groups
        for group in self.device_group_repository.find_all_devices_groups():
            event_manager.publish_device_group_event_sync(group.id, group.status.value)

    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        group = self.device_group_repository.create_device_group(device_group)
        # Publish initial state for new group
        event_manager.publish_device_group_event_sync(group.id, group.status.value)
        return group

    def delete_device_group(self, group_id: int):
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't delete while not idle")
        return self.device_group_repository.delete_device_group(group_id)

    def update_device_group(self, group_id: int, group: DeviceGroup) -> DeviceGroup:
        if group_id != group.id:
            raise BadRequestException("Can't update group id")
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't set listening value here")
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")

        updated_group = self.device_group_repository.update_device_group(group)
        # Publish status change event if status changed
        event_manager.publish_device_group_event_sync(group_id, updated_group.status.value)
        return updated_group

    def get_device_group_by_id(self, group_id: int) -> DeviceGroup:
        return self.device_group_repository.find_device_group_by_id(group_id)

    async def get_device_group_status_stream_by_id(self, group_id: int):
        """Stream device group status updates using events instead of polling"""
        # First, send the current status
        current_group = self.device_group_repository.find_device_group_by_id(group_id)
        yield f"data: {current_group.status.value}\n\n"

        # Subscribe to events for this device group
        queue = await event_manager.subscribe_to_device_group(group_id)

        try:
            while True:
                try:
                    # Wait for events with a timeout to handle client disconnections
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event.data}\n\n"
                except asyncio.TimeoutError:
                    # Send a keep-alive comment to prevent connection timeout
                    yield f": keep-alive\n\n"
        finally:
            # Clean up subscription when client disconnects
            await event_manager.unsubscribe_device_group(group_id, queue)
            print(f"Client disconnected from device group {group_id} stream")

    def get_device_group_sensors_by_id(self, group_id: int) -> Sequence[Sensor]:
        return self.device_group_repository.find_device_group_sensors_by_id(group_id)

    def update_device_group_sensors_by_id(self, group_id: int, sensor_pins: Sequence[int]) -> Sequence[Sensor]:
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")
        return self.device_group_repository.update_device_group_sensors_by_id(group_id, sensor_pins)

    def get_all_device_groups(self) -> Sequence[DeviceGroup]:
        return self.device_group_repository.find_all_devices_groups()

    def start_listening(self, group_id: int) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Group is not idle")

        # Only permit start listening if no other group is listening
        if not self.device_group_repository.are_all_groups_idle():
            raise BadRequestException("Not all groups are idle, can't start listening")

        while not self.rabbitmq_client.publish(AlarmWaiting(True, int(time.time()))):
            time.sleep(1)
        delay_execution(func=self.do_start_listening, args=(group_id,), delay_seconds=group.wait_to_start_alarm)

        group.status = DeviceGroupStatus.WAITING_TO_START_LISTENING
        updated_group = self.device_group_repository.update_device_group(group)

        # Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.WAITING_TO_START_LISTENING.value)

        return updated_group

    def stop_listening(self, group_id: int) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        if group.status != DeviceGroupStatus.LISTENING and group.status != DeviceGroupStatus.ALARM:
            raise BadRequestException("Group is not listening or in alarm")
        self.do_stop_listening(group_id)
        return self.get_device_group_by_id(group_id)

    def do_start_listening(self, group_id: int):
        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.LISTENING
        self.device_group_repository.update_device_group(group)

        # Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.LISTENING.value)

        sensors = self.get_device_group_sensors_by_id(group_id)
        for sensor in sensors:
            self.sensor_repository.update_listening(sensor, True)

        while not self.rabbitmq_client.publish(AlarmWaiting(False, int(time.time()))):
            time.sleep(1)

    def do_stop_listening(self, group_id: int):
        sensors = self.get_device_group_sensors_by_id(group_id)
        for sensor in sensors:
            self.sensor_repository.update_listening(sensor, False)

        self.alarm_manager.stop_alarm()

        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.IDLE
        self.device_group_repository.update_device_group(group)

        # Publish status change event
        event_manager.publish_device_group_event_sync(group_id, DeviceGroupStatus.IDLE.value)