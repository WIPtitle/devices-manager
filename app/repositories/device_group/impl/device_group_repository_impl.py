from typing import Sequence

from sqlmodel import select

from app.exceptions.not_found_exception import NotFoundException
from app.models.device_group import DeviceGroup
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.reed import Reed
from app.repositories.device_group.device_group_repository import DeviceGroupRepository


class DeviceGroupRepositoryImpl(DeviceGroupRepository):
    def __init__(self, database_connector):
        self.database_connector = database_connector


    def create_device_group(self, device_group: DeviceGroup):
        session = self.database_connector.get_new_session()
        session.add(device_group)
        session.commit()
        session.refresh(device_group)
        session.close()
        return device_group


    def update_device_group(self, group: DeviceGroup):
        statement = select(DeviceGroup).where(DeviceGroup.id == group.id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        if device_group is None:
            raise NotFoundException("Device group was not found")

        device_group.status = group.status
        device_group.name = group.name
        device_group.wait_to_start_alarm = group.wait_to_start_alarm
        device_group.wait_to_fire_alarm = group.wait_to_fire_alarm

        session.commit()
        session.refresh(device_group)
        session.close()
        return device_group


    def delete_device_group(self, group_id: int):
        statement = select(DeviceGroup).where(DeviceGroup.id == group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        if device_group is None:
            raise NotFoundException("Device group was not found")

        session.delete(device_group)
        session.commit()
        session.close()
        return device_group


    def find_device_group_by_id(self, device_group_id: int) -> DeviceGroup:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        session.close()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        return device_group


    def find_device_group_reeds_by_id(self, device_group_id: int) -> Sequence[Reed]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).first()
        reeds = device_group.reeds
        session.close()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        return reeds


    def update_device_group_reeds_by_id(self, device_group_id: int, reed_pins: Sequence[int]) -> Sequence[Reed]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        if device_group is None:
            raise NotFoundException("Device group was not found")

        statement = select(Reed).where(Reed.gpio_pin_number.in_(reed_pins))
        new_reeds = session.exec(statement).unique().all()

        device_group.reeds = new_reeds

        session.commit()
        session.refresh(device_group)
        reeds = device_group.reeds
        session.close()
        return reeds


    def find_all_devices_groups(self) -> Sequence[DeviceGroup]:
        statement = select(DeviceGroup)
        session = self.database_connector.get_new_session()
        device_groups = session.exec(statement).unique().all()
        session.close()
        return device_groups


    def find_listening_device_group(self) -> DeviceGroup:
        # Only a single group can be listening at a time, so return the first found or throw
        statement = select(DeviceGroup).where(DeviceGroup.status == DeviceGroupStatus.LISTENING)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        session.close()
        if device_group is None:
            raise NotFoundException("Active device group was not found")
        return device_group


    def are_all_groups_idle(self) -> bool:
        statement = select(DeviceGroup).where(DeviceGroup.status != DeviceGroupStatus.IDLE)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        session.close()
        return device_group is None
