from typing import Any

from sqlmodel import SQLModel, Field


# Recordings and cameras are shallowly linked: each recording was made with a camera, but if a camera
# gets deleted we do not want to delete the recording, so we just keep the camera ip as a link that can be
# broken and should not raise exceptions because of that.
class RecordingInputDto(SQLModel):
    camera_ip: str
    name: str


class Recording(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    camera_ip: str = Field(foreign_key="camera.ip")
    name: str
    path: str | None
    is_completed: bool | None


    @classmethod
    def from_dto(cls, dto: RecordingInputDto):
        return cls(
            camera_ip=dto.camera_ip,
            name=dto.name,
            path="/var/lib/cameras-listener/data/recordings",
            is_completed=False
        )


