from typing import Optional

from sqlmodel import SQLModel, Field


class SystemConfig(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str


class GpioServer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True)


class Mp3Server(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    audio_type_alarm: bool = Field(default=True)
    audio_type_waiting: bool = Field(default=True)
    audio_type_warning: bool = Field(default=True)
    volume_alarm: int = Field(default=100)
    volume_waiting: int = Field(default=100)
    volume_warning: int = Field(default=100)
