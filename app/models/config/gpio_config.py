from sqlalchemy import Column, Integer

from app.database.impl.base_provider import Base


class GpioConfig(Base):
    __tablename__ = "gpio_config"

    id = Column(Integer, primary_key=True, index=True)
    default_value_when_closed = Column(Integer)