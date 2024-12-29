from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship

from app.models.camera import Camera
from app.models.reed import Reed
from app.models.enums.device_group_status import DeviceGroupStatus


class DeviceGroupInputDto(SQLModel):
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int


class DeviceGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int
    status: DeviceGroupStatus
    cameras: List[Camera] = Relationship(back_populates="group", sa_relationship_kwargs={"lazy": "joined"})
    reeds: List[Reed] = Relationship(back_populates="group", sa_relationship_kwargs={"lazy": "joined"})

    @classmethod
    def from_dto(cls, dto: DeviceGroupInputDto):
        group = cls(
            id=None,
            name=dto.name,
            wait_to_start_alarm=dto.wait_to_start_alarm,
            wait_to_fire_alarm=dto.wait_to_fire_alarm,
            status=DeviceGroupStatus.IDLE,
            cameras=[],
            reeds=[]
        )
        return group