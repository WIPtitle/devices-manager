import cv2
from sqlmodel import SQLModel, Field


class CameraInputDto(SQLModel):
    ip: str
    port: int
    username: str
    password: str
    path: str
    name: str
    always_recording: bool


class Camera(SQLModel, table=True):
    ip: str = Field(primary_key=True)
    port: int
    username: str
    password: str
    path: str
    name: str
    always_recording: bool

    @classmethod
    def from_dto(cls, dto: CameraInputDto):
        return cls(
            ip=dto.ip,
            port=dto.port,
            username=dto.username,
            password=dto.password,
            path=dto.path,
            name=dto.name,
            always_recording=dto.always_recording
        )

    def is_reachable(self):
        try:
            url = f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}/{self.path}"
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                return ret
            else:
                return False
        except Exception:
            return False

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other