import time
from typing import Sequence

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.devices_manager.alarm_waiting import AlarmWaiting

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.conflict_request_exception import ConflictException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.reed.reeds_listener import ReedsListener
from app.models.camera import Camera
from app.models.device_group import DeviceGroup
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.enums.reed_status import ReedStatus
from app.models.reed import Reed
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.reed.reed_repository import ReedRepository
from app.services.device_group.device_group_service import DeviceGroupService
from app.utils.delayed_execution import delay_execution


class DeviceGroupServiceImpl(DeviceGroupService):
    def __init__(self, device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 reed_repository: ReedRepository,
                 reed_listener: ReedsListener,
                 alarm_manager: AlarmManager,
                 rabbitmq_client: RabbitMQClient):
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.reed_repository = reed_repository
        self.reed_listener = reed_listener
        self.alarm_manager = alarm_manager
        self.rabbitmq_client = rabbitmq_client


    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        return self.device_group_repository.create_device_group(device_group)


    def delete_device_group(self, group_id: int):
        return self.device_group_repository.delete_device_group(group_id)


    def update_device_group(self, group_id: int, group: DeviceGroup) -> DeviceGroup:
        if group_id != group.id:
            raise BadRequestException("Can't update group id")
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't set listening value here")
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")

        return self.device_group_repository.update_device_group(group)


    def get_device_group_by_id(self, group_id: int) -> DeviceGroup:
        return self.device_group_repository.find_device_group_by_id(group_id)


    def get_device_group_cameras_by_id(self, group_id: int) -> Sequence[Camera]:
        return self.device_group_repository.find_device_group_cameras_by_id(group_id)


    def get_device_group_reeds_by_id(self, group_id: int) -> Sequence[Reed]:
        return self.device_group_repository.find_device_group_reeds_by_id(group_id)


    def update_device_group_cameras_by_id(self, group_id: int, camera_ips: Sequence[str]) -> Sequence[Camera]:
        return self.device_group_repository.update_device_group_cameras_by_id(group_id, camera_ips)


    def update_device_group_reeds_by_id(self, group_id: int, reed_pins: Sequence[int]) -> Sequence[Reed]:
        return self.device_group_repository.update_device_group_reeds_by_id(group_id, reed_pins)


    def get_all_device_groups(self) -> Sequence[DeviceGroup]:
        return self.device_group_repository.find_all_devices_groups()


    def start_listening(self, group_id: int, force_listening: bool) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Group is not idle")

        if not force_listening:
            reeds = self.device_group_repository.find_device_group_reeds_by_id(group_id)
            if any(self.reed_listener.get_status_by_reed(reed) == ReedStatus.OPEN for reed in reeds):
                raise ConflictException("A reed is open, force listening if you want to ignore it")

        self.rabbitmq_client.publish(AlarmWaiting(int(time.time())))
        delay_execution(func=self.do_start_listening, args=group_id, delay_seconds=group.wait_to_start_alarm)

        group.status = DeviceGroupStatus.WAITING_TO_START_LISTENING
        self.device_group_repository.update_device_group(group)

        return self.get_device_group_by_id(group_id)


    def stop_listening(self, group_id: int) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        if group.status != DeviceGroupStatus.LISTENING or group.status != DeviceGroupStatus.ALARM:
            raise BadRequestException("Group is not listening or in alarm")
        self.do_stop_listening(group_id)
        return self.get_device_group_by_id(group_id)


    def do_start_listening(self, group_id: int):
        cameras = self.get_device_group_cameras_by_id(group_id)
        reeds = self.get_device_group_reeds_by_id(group_id)

        for camera in cameras:
            self.camera_repository.update_listening(camera, True)

        for reed in reeds:
            if self.reed_listener.get_status_by_reed(reed) != ReedStatus.OPEN:
                self.reed_repository.update_listening(reed, True)

        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.LISTENING
        self.device_group_repository.update_device_group(group)


    def do_stop_listening(self, group_id: int):
        cameras = self.get_device_group_cameras_by_id(group_id)
        reeds = self.get_device_group_reeds_by_id(group_id)

        for camera in cameras:
            self.camera_repository.update_listening(camera, False)

        for reed in reeds:
            self.reed_repository.update_listening(reed, False)

        # Emit a stop alarm event even if not in alarm state, at worst it will be ignored
        self.alarm_manager.stop_alarm()

        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.IDLE
        self.device_group_repository.update_device_group(group)
