from app.config.bindings import inject
from app.models.disk_usage import DiskUsage
from app.models.recording import get_recordings_path
from app.routers.router_wrapper import RouterWrapper


class DiskUsageRouter(RouterWrapper):
    @inject
    def __init__(self):
        super().__init__(prefix=f"/disk-usage")


    def _define_routes(self):
        # Basic CRUD
        @self.router.get("/")
        def get_usage() -> DiskUsage:
            return DiskUsage.from_path(get_recordings_path())
