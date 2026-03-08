import subprocess
from typing import Optional

from sqlmodel import SQLModel, Field


class CameraInputDto(SQLModel):
    ip: str
    port: int
    username: str
    password: str
    path: str
    name: str
    always_recording: bool
    detection_mode: Optional[str] = None
    detection_roi: Optional[str] = None


class Camera(SQLModel, table=True):
    ip: str = Field(primary_key=True)
    port: int
    username: str
    password: str
    path: str
    name: str
    always_recording: bool
    detection_mode: Optional[str] = Field(default=None)
    detection_roi: Optional[str] = Field(default=None)

    @classmethod
    def from_dto(cls, dto: CameraInputDto):
        return cls(
            ip=dto.ip,
            port=dto.port,
            username=dto.username,
            password=dto.password,
            path=dto.path,
            name=dto.name,
            always_recording=dto.always_recording,
            detection_mode=dto.detection_mode,
            detection_roi=dto.detection_roi,
        )

    def rtsp_url(self) -> str:
        if self.username and self.password:
            return f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}/{self.path}"
        return f"rtsp://{self.ip}:{self.port}/{self.path}"

    def is_reachable(self):
        try:
            command = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-timeout", "5000000",
                "-i", self.rtsp_url(),
                "-t", "1",
                "-f", "null",
                "-"
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other