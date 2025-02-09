import os
from typing import BinaryIO, Sequence

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse, FileResponse

from app.exceptions.bad_request_exception import BadRequestException
from app.jobs.recording.recordings_manager import RecordingsManager
from app.models.recording import Recording, RecordingInputDto
from app.repositories.camera.camera_repository import CameraRepository
from app.repositories.recording.recording_repository import RecordingRepository
from app.services.recording.recording_service import RecordingService
from app.utils.delayed_execution import delay_execution


class RecordingServiceImpl(RecordingService):
    def __init__(self, recording_repository: RecordingRepository, camera_repository: CameraRepository, recording_manager: RecordingsManager):
        self.recording_repository = recording_repository
        self.camera_repository = camera_repository
        self.recording_manager = recording_manager

        # If on boot some recording were not stopped properly, set them as stopped here
        for recording in self.recording_repository.find_all():
            if not recording.is_completed:
                self.recording_repository.set_stopped(recording)


    def get_by_id(self, rec_id: int) -> Recording:
        return self.recording_repository.find_by_id(rec_id)


    def create_and_start_recording(self, recording: Recording, auto_restart: bool) -> Recording:
        camera = self.camera_repository.find_by_ip(recording.camera_ip) # will throw if not found

        if not self.recording_manager.is_recording(recording.camera_ip):
            recording = self.recording_repository.create(recording)
            self.recording_manager.start_recording(recording)

            if auto_restart:
                delay_execution(
                    func=self.restart,
                    args=(camera.ip,),
                    delay_seconds= 60 * 60) # restart recording after n minutes to have separate files

            return recording
        else:
            raise BadRequestException("Recording already started")


    def restart(self, camera_ip: str):
        try:
            print(f"Restarting recording for camera on {camera_ip}")
            self.stop_by_camera_ip(camera_ip)
            camera = self.camera_repository.find_by_ip(camera_ip)
            auto_restart = camera.always_recording
            self.create_and_start_recording(Recording.from_dto(RecordingInputDto(camera_ip=camera_ip, always_recording=camera.always_recording)), auto_restart=auto_restart)
        except Exception as e:
            pass


    def stop_by_camera_ip(self, camera_ip: str) -> Recording:
        recording = self.recording_manager.get_current_recording_by_camera_ip(camera_ip)
        if recording is not None:
            self.recording_manager.stop_recording(recording)
            self.recording_repository.set_stopped(recording)
        return recording


    def delete_by_id(self, rec_id: int) -> Recording:
        recording = self.recording_repository.delete_by_id(rec_id)
        if not recording.is_completed:
            raise BadRequestException("Recording is not yet completed")
        self.recording_manager.delete_recording_file(recording)
        return recording


    def delete_all(self) -> Sequence[Recording]:
        recordings = self.recording_repository.find_all()
        # less efficient than delete all at db level but can't be fucked right now
        for recording in recordings:
            # do not delete recordings that are still going on
            if recording.is_completed:
                self.delete_by_id(recording.id)
        return recordings


    def get_all(self) -> Sequence[Recording]:
        return self.recording_repository.find_all()


    def stream(self, request: Request, rec_id: int):
        recording = self.recording_repository.find_by_id(rec_id)
        if not recording.is_completed:
            raise BadRequestException("Recording is not yet completed")

        file_path = os.path.join(recording.path, recording.name)

        return range_requests_response(
            request, file_path=file_path, content_type="video/x-matroska"
        )


    def download(self, rec_id: int):
        recording = self.recording_repository.find_by_id(rec_id)
        if not recording.is_completed:
            raise BadRequestException("Recording is not yet completed")

        file_path = os.path.join(recording.path, recording.name)
        return FileResponse(file_path, media_type="video/x-matroska", filename=recording.name)


# Shamelessly copied from https://github.com/fastapi/fastapi/issues/1240#issuecomment-1055396884 to let
# frontend seek in the video
def send_bytes_range_requests(
    file_obj: BinaryIO, start: int, end: int, chunk_size: int = 10_000
):
    """Send a file in chunks using Range Requests specification RFC7233

    `start` and `end` parameters are inclusive due to specification
    """
    with file_obj as f:
        f.seek(start)
        while (pos := f.tell()) <= end:
            read_size = min(chunk_size, end + 1 - pos)
            yield f.read(read_size)


def _get_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    def _invalid_range():
        return HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f"Invalid request range (Range:{range_header!r})",
        )

    try:
        h = range_header.replace("bytes=", "").split("-")
        start = int(h[0]) if h[0] != "" else 0
        end = int(h[1]) if h[1] != "" else file_size - 1
    except ValueError:
        raise _invalid_range()

    if start > end or start < 0 or end > file_size - 1:
        raise _invalid_range()
    return start, end


def range_requests_response(
    request: Request, file_path: str, content_type: str
):
    """Returns StreamingResponse using Range Requests of a given file"""

    file_size = os.stat(file_path).st_size
    range_header = request.headers.get("range")

    headers = {
        "content-type": content_type,
        "accept-ranges": "bytes",
        "content-encoding": "identity",
        "content-length": str(file_size),
        "access-control-expose-headers": (
            "content-type, accept-ranges, content-length, "
            "content-range, content-encoding"
        ),
    }
    start = 0
    end = file_size - 1
    status_code = status.HTTP_200_OK

    if range_header is not None:
        start, end = _get_range_header(range_header, file_size)
        size = end - start + 1
        headers["content-length"] = str(size)
        headers["content-range"] = f"bytes {start}-{end}/{file_size}"
        status_code = status.HTTP_206_PARTIAL_CONTENT

    return StreamingResponse(
        send_bytes_range_requests(open(file_path, mode="rb"), start, end),
        headers=headers,
        status_code=status_code,
    )