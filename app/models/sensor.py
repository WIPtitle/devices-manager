from sqlmodel import SQLModel, Field


class SensorInputDto(SQLModel):
    gpio_pin_number: int
    name: str


class Sensor(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    name: str
    listening: bool

    @classmethod
    def from_dto(cls, dto: SensorInputDto):
        return cls(
            gpio_pin_number=dto.gpio_pin_number,
            name=dto.name,
            listening=False
        )