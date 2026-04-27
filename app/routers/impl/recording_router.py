from typing import Sequence
from fastapi import Request, Query

from app.clients.auth_client import AuthClient
from app.config.bindings import inject
from app.exceptions.authorization_exception import AuthorizationException
from app.models.enums.recording_type import RecordingType
from app.models.recording import Recording
from app.routers.router_wrapper import RouterWrapper
from app.services.recording.recording_service import RecordingService


class RecordingRouter(RouterWrapper):
    @inject
    def __init__(self, recording_service: RecordingService, auth_client: AuthClient):
        super().__init__(prefix=f"/recording")
        self.recording_service = recording_service
        self.auth_client = auth_client

    def _define_routes(self):
        # Basic CRUD
        @self.router.get("/{rec_id}")
        async def get_recording_by_id(request: Request, rec_id: int) -> Recording:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.recording_service.get_by_id(rec_id)

        @self.router.delete("/{rec_id}")
        async def delete_recording_by_id(request: Request, rec_id: int) -> Recording:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.recording_service.delete_by_id(rec_id)

        @self.router.delete("/")
        async def delete_recordings(request: Request) -> Sequence[Recording]:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.recording_service.delete_all()

        @self.router.get("/{rec_id}/stream")
        async def stream_recording(request: Request, rec_id: int):
            token = request.headers.get("Authorization")
            if token is None and request.query_params.get("auth_token") is not None:
                token = "Bearer " + request.query_params.get("auth_token")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.recording_service.stream(request, rec_id)

        @self.router.get("/{rec_id}/download")
        async def download_recording(request: Request, rec_id: int):
            token = request.headers.get("Authorization")
            if token is None and request.query_params.get("auth_token") is not None:
                token = "Bearer " + request.query_params.get("auth_token")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.recording_service.download(rec_id)

        # Other endpoints
        @self.router.get("/", operation_id="get_all_recordings_with_slash")
        @self.router.get("", operation_id="get_all_recordings_without_slash")
        async def get_all_recordings(
                request: Request,
                offset: int = 0,
                rec_type: RecordingType | None = Query(default=None, alias="type"),
                camera_ip: str | None = Query(default=None, alias="camera_ip")
        ) -> Sequence[Recording]:
            token = request.headers.get("Authorization")
            user = await self.auth_client.get_authenticated_user(token)
            if user is None or "ACCESS_RECORDINGS" not in user.permissions:
                raise AuthorizationException("Not authorized")
            return self.recording_service.get_all_paginated(offset=offset, recording_type=rec_type, camera_ip=camera_ip)