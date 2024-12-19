from app.config.bindings import inject
from app.models.disk_usage import DiskUsage
from app.models.recording import get_recordings_path
from app.routers.router_wrapper import RouterWrapper


class DiskUsageRouter(RouterWrapper):
    @inject
    def __init__(self):
        super().__init__(prefix=f"/disk-usage")


    def _define_routes(self):
        @self.router.get("/", operation_id="get_disk_usage_with_slash")
        @self.router.get("", operation_id="get_disk_usage_without_slash")
        def get_usage() -> DiskUsage:
            return DiskUsage.from_path(get_recordings_path())
