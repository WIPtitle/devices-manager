from app.repositories.device_group.device_group_repository import DeviceGroupRepository
from app.services.device_group.device_group_service import DeviceGroupService


class DeviceGroupServiceImpl(DeviceGroupService):
    def __init__(self, device_group_repository: DeviceGroupRepository):
        self.device_group_repository = device_group_repository

