import uuid
from sqlmodel import SQLModel, Field


class SensorInputDto(SQLModel):
    gpio_pin_number: int
    gpio_server_url: str
    name: str


class Sensor(SQLModel, table=True):
    id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    gpio_pin_number: int = Field(index=True)
    gpio_server_url: str = Field(index=True)
    name: str
    listening: bool

    @classmethod
    def from_dto(cls, dto: SensorInputDto):
        return cls(
            gpio_pin_number=dto.gpio_pin_number,
            gpio_server_url=dto.gpio_server_url,
            name=dto.name,
            listening=False
        )

    class Config:
        # Create a unique constraint on the combination of gpio_pin_number and gpio_server_url
        # This will be handled in the repository implementation
        pass