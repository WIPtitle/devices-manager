import subprocess

from sqlmodel import SQLModel, Field


class CameraInputDto(SQLModel):
    ip: str
    port: int
    username: str
    password: str
    path: str
    name: str


class Camera(SQLModel, table=True):
    ip: str = Field(primary_key=True)
    port: int
    username: str
    password: str
    path: str
    name: str


    @classmethod
    def from_dto(cls, dto: CameraInputDto):
        return cls(
            ip=dto.ip,
            port=dto.port,
            username=dto.username,
            password=dto.password,
            path=dto.path,
            name=dto.name
        )

    def is_reachable(self):
        try:
            command = [
                "ffmpeg",
                "-i", f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}/{self.path}",
                "-t", "1",
                "-f", "null",
                "-"
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception:
            return False

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other
