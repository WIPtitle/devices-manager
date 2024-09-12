from app.config.bindings import inject
from app.routers.router_wrapper import RouterWrapper
from app.services.device_group.device_group_service import DeviceGroupService


class DeviceGroupRouter(RouterWrapper):
    @inject
    def __init__(self, device_group_service: DeviceGroupService):
        super().__init__(prefix=f"/device-group")
        self.device_group_service = device_group_service


    def _define_routes(self):
        # Basic CRUD
        print("Ok")
