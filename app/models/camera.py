import cv2
from sqlmodel import SQLModel, Field


class Camera(SQLModel, table=True):
    ip: str = Field(primary_key=True)
    port: int
    username: str
    password: str
    path: str
    sensibility: int # Percentage of camera area for minimum area of motion


    def is_reachable(self):
        cap = cv2.VideoCapture(f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}/{self.path}")
        if not cap.isOpened():
            return False
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return False
        return True

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other
