from typing import Sequence

from app.config.bindings import inject
from app.models.recording import Recording
from app.routers.router_wrapper import RouterWrapper
from app.services.recording.recording_service import RecordingService


class RecordingRouter(RouterWrapper):
    @inject
    def __init__(self, recording_service: RecordingService):
        super().__init__(prefix=f"/recording")
        self.recording_service = recording_service


    def _define_routes(self):
        # Basic CRUD
        @self.router.get("/{rec_id}")
        def get_recording_by_id(rec_id: int) -> Recording:
            return self.recording_service.get_by_id(rec_id)


        @self.router.delete("/{rec_id}")
        def delete_recording_by_id(rec_id: int) -> Recording:
            return self.recording_service.delete_by_id(rec_id)


        @self.router.get("/{rec_id}/stream")
        def stream_recording(rec_id: int):
            return self.recording_service.stream(rec_id)


        @self.router.get("/{rec_id}/download")
        def download_recording(rec_id: int):
            return self.recording_service.download(rec_id)


        # Other endpoints
        @self.router.get("/", operation_id="get_all_recordings_with_slash")
        @self.router.get("", operation_id="get_all_recordings_without_slash")
        def get_all_recordings() -> Sequence[Recording]:
            return self.recording_service.get_all()
