from typing import List

from sqlmodel import select

from app.exceptions.not_found_exception import NotFoundException
from app.models.device_group import Device, DeviceGroup, DeviceGroupLink
from app.repositories.device_group.device_group_repository import DeviceGroupRepository


class DeviceGroupRepositoryImpl(DeviceGroupRepository):
    def __init__(self, database_connector):
        self.database_connector = database_connector


    def create_device(self, device: Device):
        session = self.database_connector.get_session()
        session.add(device)
        session.commit()
        session.refresh(device)
        return device


    def delete_device(self, device_id: int):
        session = self.database_connector.get_session()
        device = self.find_device_by_id(device_id)

        session.query(DeviceGroupLink).filter(DeviceGroupLink.device_id == device_id).delete()

        session.delete(device)
        session.commit()
        return device


    def create_device_group(self, device_group: DeviceGroup):
        session = self.database_connector.get_session()
        session.add(device_group)
        session.commit()
        session.refresh(device_group)
        return device_group


    def delete_device_group(self, group_id: int):
        session = self.database_connector.get_session()
        device_group = self.find_device_group_by_group_id(group_id)

        session.query(DeviceGroupLink).filter(DeviceGroupLink.group_id == group_id).delete()

        session.delete(device_group)
        session.commit()
        return device_group


    def update_device_group(self, group: DeviceGroup):
        session = self.database_connector.get_session()
        device_group = self.find_device_group_by_group_id(group.id)
        device_group.name = group.name
        session.commit()
        session.refresh(device_group)
        return device_group


    def update_devices_in_group(self, group_id: int, devices: list[Device]) -> List[Device]:
        session = self.database_connector.get_session()

        statement = select(DeviceGroupLink).where(DeviceGroupLink.group_id == group_id)
        current_links = session.exec(statement).all()

        current_device_ids = {link.device_id for link in current_links}
        new_device_ids = {device.id for device in devices}

        devices_to_add = new_device_ids - current_device_ids
        devices_to_remove = current_device_ids - new_device_ids

        for device_id in devices_to_remove:
            link = session.exec(select(DeviceGroupLink).where(DeviceGroupLink.device_id == device_id,
                                                              DeviceGroupLink.group_id == group_id)).first()
            if link:
                session.delete(link)

        for device_id in devices_to_add:
            link = DeviceGroupLink(device_id=device_id, group_id=group_id)
            session.add(link)

        session.commit()
        return self.find_device_list_by_id(group_id)


    def find_device_by_id(self, device_id: int) -> Device:
        statement = select(Device).where(Device.id == device_id)
        device = self.database_connector.get_session().exec(statement).first()
        if device is None:
            raise NotFoundException("Device was not found")
        return device


    def find_device_group_by_group_id(self, device_group_id: int) -> DeviceGroup:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        device_group = self.database_connector.get_session().exec(statement).first()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        return device_group


    def find_device_group_list_by_device_id(self, device_id: int) -> List[DeviceGroup]:
        statement = select(DeviceGroup).join(DeviceGroupLink).where(DeviceGroupLink.device_id == device_id)
        device_groups = self.database_connector.get_session().exec(statement)
        return device_groups


    def find_device_list_by_id(self, group_id: int) -> List[Device]:
        device_group = self.find_device_group_by_group_id(group_id)
        if device_group is None:
            raise NotFoundException("DeviceGroup was not found")
        return device_group.devices
