import datetime

from sqlmodel import SQLModel, Field

from app.models.enums.recording_type import RecordingType


def get_alarm_recordings_path():
    return "/var/lib/devices-manager/data/alarm_recordings"

def get_recordings_path():
    return "/var/lib/devices-manager/data/recordings"


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
        file_name = f"{start_time}_{dto.camera_ip}.mp4"

        if dto.always_recording:
            path = get_recordings_path()
            rec_type = RecordingType.NORMAL
        else:
            path = get_alarm_recordings_path()
            rec_type = RecordingType.ALARM

        return cls(
            camera_ip=dto.camera_ip,
            name=file_name,
            path=path,
            type=rec_type,
            is_completed=False
        )