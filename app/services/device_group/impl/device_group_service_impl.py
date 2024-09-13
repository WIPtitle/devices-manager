from typing import List

from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.alarm.alarm_manager import AlarmManager
from app.models.device_group import Device, DeviceGroup
from app.models.enums.device_type import DeviceType
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.services.device_group.device_group_service import DeviceGroupService
from app.utils.raspberry_check import is_raspberry


class DeviceGroupServiceImpl(DeviceGroupService):
    def __init__(self, device_group_repository: DeviceGroupRepository, camera_repository: CameraRepository, alarm_manager: AlarmManager):
        self.device_group_repository = device_group_repository
        self.camera_repository = camera_repository
        self.reed_repository = None
        self.alarm_manager = alarm_manager


    def set_reed_repository(self, repo):
        if is_raspberry():
            from app.repositories.reed.reed_repository import ReedRepository
            self.reed_repository: ReedRepository = repo


    def create_device_group(self, device_group: DeviceGroup) -> DeviceGroup:
        return self.device_group_repository.create_device_group(device_group)


    def delete_device_group(self, group_id: int):
        return self.device_group_repository.delete_device_group(group_id)


    def update_device_group(self, group_id: int, group: DeviceGroup) -> DeviceGroup:
        if group_id != group.id:
            raise BadRequestException("Can't update group id")
        return self.device_group_repository.update_device_group(group)


    def update_devices_in_group(self, group_id: int, device_ids: List[int]) -> List[Device]:
        device_entities = [self.device_group_repository.find_device_by_id(device_id) for device_id in device_ids]
        devices_list = self.device_group_repository.update_devices_in_group(group_id, device_entities)
        return devices_list


    def get_device_by_id(self, device_id: int) -> Device:
        return self.device_group_repository.find_device_by_id(device_id)


    def get_device_group_by_id(self, group_id: int) -> DeviceGroup:
        return self.device_group_repository.find_device_group_by_id(group_id)


    def get_device_list_by_id(self, group_id: int) -> List[Device]:
        return self.device_group_repository.find_device_list_by_id(group_id)


    def start_listening(self, group_id: int) -> DeviceGroup:
        devices = self.get_device_list_by_id(group_id)
        for device in devices:
            if device.device_type == DeviceType.RTSP_CAMERA:
                camera = self.camera_repository.find_by_generic_device_id(device.id)
                self.camera_repository.update_listening(camera, True)
            elif device.device_type == DeviceType.MAGNETIC_REED:
                if is_raspberry():
                    from app.repositories.reed.reed_repository import ReedRepository
                    repo: ReedRepository = self.reed_repository
                    reed = repo.find_by_generic_device_id(device.id)
                    repo.update_listening(reed, True)
        return self.get_device_group_by_id(group_id)


    def stop_listening(self, group_id: int) -> DeviceGroup:
        devices = self.get_device_list_by_id(group_id)
        for device in devices:
            if device.device_type == DeviceType.RTSP_CAMERA:
                camera = self.camera_repository.find_by_generic_device_id(device.id)
                self.camera_repository.update_listening(camera, False)
            elif device.device_type == DeviceType.MAGNETIC_REED:
                if is_raspberry():
                    from app.repositories.reed.reed_repository import ReedRepository
                    repo: ReedRepository = self.reed_repository
                    reed = repo.find_by_generic_device_id(device.id)
                    repo.update_listening(reed, False)

        all_cameras = self.camera_repository.find_all()
        all_cameras_not_listening = all(not camera.listening for camera in all_cameras)
        if is_raspberry():
            from app.repositories.reed.reed_repository import ReedRepository
            repo: ReedRepository = self.reed_repository
            all_reeds = repo.find_all()
            all_reeds_not_listening = all(not reed.listening for reed in all_reeds)
            if all_cameras_not_listening and all_reeds_not_listening:
                self.alarm_manager.on_all_devices_stopped_listening()
        else:
            if all_cameras_not_listening:
                self.alarm_manager.on_all_devices_stopped_listening()

        return self.get_device_group_by_id(group_id)
