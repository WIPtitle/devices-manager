from sqlmodel import SQLModel, Field


class PirInputDto(SQLModel):
    gpio_pin_number: int
    name: str


class Pir(SQLModel, table=True):
    gpio_pin_number: int = Field(primary_key=True)
    name: str
    listening: bool

    @classmethod
    def from_dto(cls, dto: PirInputDto):
        return cls(
            gpio_pin_number=dto.gpio_pin_number,
            name=dto.name,
            listening=False
        )
