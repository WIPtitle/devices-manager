from typing import Sequence
from sqlmodel import select

from app.exceptions.not_found_exception import NotFoundException
from app.models.camera import Camera
from app.models.device_group import DeviceGroup
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.sensor import Sensor
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
        device_group.arming_session_id = group.arming_session_id

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

    def find_device_group_sensors_by_id(self, device_group_id: int) -> Sequence[Sensor]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).first()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        sensors = device_group.sensors
        session.close()
        return sensors

    def update_device_group_sensors_by_id(self, device_group_id: int, sensor_ids: Sequence[str]) -> Sequence[Sensor]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        if device_group is None:
            raise NotFoundException("Device group was not found")

        statement = select(Sensor).where(Sensor.id.in_(sensor_ids))
        new_sensors = session.exec(statement).unique().all()

        device_group.sensors = new_sensors

        session.commit()
        session.refresh(device_group)
        sensors = device_group.sensors
        session.close()
        return sensors

    def find_device_group_cameras_by_id(self, device_group_id: int) -> Sequence[Camera]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).first()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        cameras = device_group.cameras
        session.close()
        return cameras

    def update_device_group_cameras_by_id(self, device_group_id: int, camera_ips: Sequence[str]) -> Sequence[Camera]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        session = self.database_connector.get_new_session()
        device_group = session.exec(statement).unique().first()
        if device_group is None:
            raise NotFoundException("Device group was not found")

        statement = select(Camera).where(Camera.ip.in_(camera_ips))
        new_cameras = session.exec(statement).unique().all()

        device_group.cameras = new_cameras

        session.commit()
        session.refresh(device_group)
        cameras = device_group.cameras
        session.close()
        return cameras

    def find_all_devices_groups(self) -> Sequence[DeviceGroup]:
        statement = select(DeviceGroup)
        session = self.database_connector.get_new_session()
        device_groups = session.exec(statement).unique().all()
        session.close()
        return device_groups

    def find_listening_device_group(self) -> DeviceGroup:
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