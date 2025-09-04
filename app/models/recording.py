import datetime
import logging

from sqlmodel import SQLModel, Field

from app.models.enums.recording_type import RecordingType

logger = logging.getLogger(__name__)


# separation between normal recordings and alarm recordings
def get_alarm_recordings_path():
    return "/var/lib/devices-manager/data/alarm_recordings"

def get_recordings_path():
    return "/var/lib/devices-manager/data/recordings"

# Recordings and cameras are shallowly linked: each recording was made with a camera, but if a camera
# gets deleted we do not want to delete the recording, so we just keep the camera ip as a link that can be
# broken and should not raise exceptions because of that.
class RecordingInputDto(SQLModel):
    camera_ip: str
    always_recording: bool


class Recording(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    camera_ip: str
    name: str | None
    path: str | None
    type: RecordingType | None
    is_completed: bool | None


    @classmethod
    def from_dto(cls, dto: RecordingInputDto):
        start_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        file_name = f"{start_time}_{dto.camera_ip}.mkv"

        if dto.always_recording:
            path = get_recordings_path()
            rec_type = RecordingType.NORMAL
        else:
            path = get_alarm_recordings_path()
            rec_type = RecordingType.ALARM

        logger.debug(f"Creating Recording: camera_ip={dto.camera_ip}, always_recording={dto.always_recording}, type={rec_type}, path={path}, name={file_name}")

        return cls(
            camera_ip=dto.camera_ip,
            name=file_name,
            path=path,
            type=rec_type,
            is_completed=False
        )