from typing import Sequence

from sqlmodel import select

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.camera import Camera
from app.models.reed import Reed
from app.models.device_group import DeviceGroup
from app.repositories.device_group.device_group_repository import DeviceGroupRepository


class DeviceGroupRepositoryImpl(DeviceGroupRepository):
    def __init__(self, database_connector):
        self.database_connector = database_connector


    def create_device_group(self, device_group: DeviceGroup):
        session = self.database_connector.get_session()
        session.add(device_group)
        session.commit()
        session.refresh(device_group)
        return device_group


    def update_device_group(self, group: DeviceGroup):
        session = self.database_connector.get_session()
        device_group = self.find_device_group_by_id(group.id)

        # Do not update status, that is calculated
        device_group.name = group.name
        device_group.wait_to_start_alarm = group.wait_to_start_alarm
        device_group.wait_to_fire_alarm = group.wait_to_fire_alarm

        session.commit()
        session.refresh(device_group)
        return device_group


    def delete_device_group(self, group_id: int):
        session = self.database_connector.get_session()
        device_group = self.find_device_group_by_id(group_id)

        # Set group_id to None for all cameras in the group
        for camera in device_group.cameras:
            camera.group_id = None

        # Set group_id to None for all reeds in the group
        for reed in device_group.reeds:
            reed.group_id = None

        session.delete(device_group)
        session.commit()
        return device_group


    def find_device_group_by_id(self, device_group_id: int) -> DeviceGroup:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        device_group = self.database_connector.get_session().exec(statement).first()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        return device_group


    def find_device_group_cameras_by_id(self, device_group_id: int) -> Sequence[Camera]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        device_group = self.database_connector.get_session().exec(statement).first()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        return device_group.cameras


    def find_device_group_reeds_by_id(self, device_group_id: int) -> Sequence[Reed]:
        statement = select(DeviceGroup).where(DeviceGroup.id == device_group_id)
        device_group = self.database_connector.get_session().exec(statement).first()
        if device_group is None:
            raise NotFoundException("Device group was not found")
        return device_group.reeds


    def update_device_group_cameras_by_id(self, device_group_id: int, camera_ips: Sequence[str]) -> Sequence[Camera]:
        session = self.database_connector.get_session()
        device_group = self.find_device_group_by_id(device_group_id)

        # Check and update existing cameras
        for camera in device_group.cameras:
            if camera.ip not in camera_ips:
                camera.group_id = None

        statement = select(Camera).where(Camera.ip.in_(camera_ips))
        new_cameras = session.exec(statement).all()

        for camera in new_cameras:
            if camera.group_id is not None and camera.group_id != device_group_id:
                raise BadRequestException(f"Camera with IP {camera.ip} is already part of another group")
            camera.group_id = device_group_id

        device_group.cameras = new_cameras

        session.commit()
        session.refresh(device_group)
        return device_group.cameras


    def update_device_group_reeds_by_id(self, device_group_id: int, reed_pins: Sequence[int]) -> Sequence[Reed]:
        session = self.database_connector.get_session()
        device_group = self.find_device_group_by_id(device_group_id)

        # Check and update existing reeds
        for reed in device_group.reeds:
            if reed.gpio_pin_number not in reed_pins:
                reed.group_id = None

        statement = select(Reed).where(Reed.gpio_pin_number.in_(reed_pins))
        new_reeds = session.exec(statement).all()

        for reed in new_reeds:
            if reed.group_id is not None and reed.group_id != device_group_id:
                raise BadRequestException(f"Reed with GPIO pin {reed.gpio_pin_number} is already part of another group")
            reed.group_id = device_group_id

        device_group.reeds = new_reeds

        session.commit()
        session.refresh(device_group)
        return device_group.reeds


    def find_all_devices_groups(self) -> Sequence[DeviceGroup]:
        statement = select(DeviceGroup)
        device_groups = self.database_connector.get_session().exec(statement).all()
        return device_groups
