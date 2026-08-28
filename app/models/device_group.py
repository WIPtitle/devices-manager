from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from app.models.enums.device_group_status import DeviceGroupStatus
from app.models.sensor import Sensor
from app.models.camera import Camera


class DeviceGroupInputDto(SQLModel):
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int


class DeviceGroupSensorLink(SQLModel, table=True):
    device_group_id: int = Field(foreign_key="devicegroup.id", primary_key=True)
    sensor_id: str = Field(foreign_key="sensor.id", primary_key=True)


class DeviceGroupCameraLink(SQLModel, table=True):
    device_group_id: int = Field(foreign_key="devicegroup.id", primary_key=True)
    camera_ip: str = Field(foreign_key="camera.ip", primary_key=True)


class DeviceGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    wait_to_start_alarm: int
    wait_to_fire_alarm: int
    status: DeviceGroupStatus
    arming_session_id: Optional[str] = Field(default=None)
    sensors: List[Sensor] = Relationship(link_model=DeviceGroupSensorLink)
    cameras: List[Camera] = Relationship(link_model=DeviceGroupCameraLink)

    @classmethod
    def from_dto(cls, dto: DeviceGroupInputDto):
        group = cls(
            id=None,
            name=dto.name,
            wait_to_start_alarm=dto.wait_to_start_alarm,
            wait_to_fire_alarm=dto.wait_to_fire_alarm,
            status=DeviceGroupStatus.IDLE,
            sensors=[],
            cameras=[],
        )
        return group