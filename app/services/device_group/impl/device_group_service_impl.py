import asyncio
import time
from typing import Sequence

from rabbitmq_sdk.client.rabbitmq_client import RabbitMQClient
from rabbitmq_sdk.event.impl.devices_manager.alarm_waiting import AlarmWaiting

from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.jobs.reed.reeds_listener import ReedsListener
from app.models.device_group import DeviceGroup
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.pir import Pir
from app.models.reed import Reed
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.repositories.pir.pir_repository import PirRepository
from app.repositories.reed.reed_repository import ReedRepository
from app.services.device_group.device_group_service import DeviceGroupService
from app.utils.delayed_execution import delay_execution


class DeviceGroupServiceImpl(DeviceGroupService):
    def __init__(self, device_group_repository: DeviceGroupRepository,
                 camera_repository: CameraRepository,
                 reed_repository: ReedRepository,
                 pir_repository: PirRepository,
                 alarm_manager: AlarmManager,
                 rabbitmq_client: RabbitMQClient):
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.reed_repository = reed_repository
        self.pir_repository = pir_repository
        self.alarm_manager = alarm_manager
        self.rabbitmq_client = rabbitmq_client


    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        return self.device_group_repository.create_device_group(device_group)


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

        return self.device_group_repository.update_device_group(group)


    def get_device_group_by_id(self, group_id: int) -> DeviceGroup:
        return self.device_group_repository.find_device_group_by_id(group_id)


    async def get_device_group_status_stream_by_id(self, group_id: int):
        while True:
            await asyncio.sleep(1)
            yield f"data: {self.device_group_repository.find_device_group_by_id(group_id).status}\n\n"


    def get_device_group_reeds_by_id(self, group_id: int) -> Sequence[Reed]:
        return self.device_group_repository.find_device_group_reeds_by_id(group_id)


    def update_device_group_reeds_by_id(self, group_id: int, reed_pins: Sequence[int]) -> Sequence[Reed]:
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")
        return self.device_group_repository.update_device_group_reeds_by_id(group_id, reed_pins)


    def get_device_group_pirs_by_id(self, group_id: int) -> Sequence[Pir]:
        return self.device_group_repository.find_device_group_pirs_by_id(group_id)


    def update_device_group_pirs_by_id(self, group_id: int, pir_pins: Sequence[int]) -> Sequence[Pir]:
        if self.device_group_repository.find_device_group_by_id(group_id).status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Can't update while not idle")
        return self.device_group_repository.update_device_group_pirs_by_id(group_id, pir_pins)



    def get_all_device_groups(self) -> Sequence[DeviceGroup]:
        return self.device_group_repository.find_all_devices_groups()


    def start_listening(self, group_id: int) -> DeviceGroup:
        group = self.get_device_group_by_id(group_id)
        if group.status != DeviceGroupStatus.IDLE:
            raise BadRequestException("Group is not idle")

        # Only permit start listening if no other group is listening or waiting to, so we are sure only one group is listening at a time
        if not self.device_group_repository.are_all_groups_idle():
            raise BadRequestException("Not all groups are idle, can't start listening")

        while not self.rabbitmq_client.publish(AlarmWaiting(True, int(time.time()))):
            time.sleep(1)
        delay_execution(func=self.do_start_listening, args=(group_id, ), delay_seconds=group.wait_to_start_alarm)

        group.status = DeviceGroupStatus.WAITING_TO_START_LISTENING
        self.device_group_repository.update_device_group(group)

        return self.get_device_group_by_id(group_id)


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

        reeds = self.get_device_group_reeds_by_id(group_id)
        for reed in reeds:
            self.reed_repository.update_listening(reed, True)

        pirs = self.get_device_group_pirs_by_id(group_id)
        for pir in pirs:
            self.pir_repository.update_listening(pir, True)

        while not self.rabbitmq_client.publish(AlarmWaiting(False, int(time.time()))):
            time.sleep(1)


    def do_stop_listening(self, group_id: int):
        reeds = self.get_device_group_reeds_by_id(group_id)
        for reed in reeds:
            self.reed_repository.update_listening(reed, False)

        pirs = self.get_device_group_pirs_by_id(group_id)
        for pir in pirs:
            self.pir_repository.update_listening(pir, False)

        self.alarm_manager.stop_alarm()

        group = self.device_group_repository.find_device_group_by_id(group_id)
        group.status = DeviceGroupStatus.IDLE
        self.device_group_repository.update_device_group(group)
