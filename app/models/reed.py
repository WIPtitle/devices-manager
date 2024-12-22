from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class ReedInputDto(SQLModel):
    gpio_pin_number: int
    name: str
    normally_closed: bool
    vcc: bool


class Reed(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    name: str
    normally_closed: bool
    vcc: bool
    listening: bool
    group_id: Optional[int] = Field(default=None, foreign_key="devicegroup.id")
    group: Optional["DeviceGroup"] = Relationship(back_populates="reeds")

    @classmethod
    def from_dto(cls, dto: ReedInputDto):
        return cls(
            gpio_pin_number=dto.gpio_pin_number,
            name=dto.name,
            normally_closed=dto.normally_closed,
            vcc=dto.vcc,
            listening=False,
            group_id=None,
        )
