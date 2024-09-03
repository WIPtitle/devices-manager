from typing import Optional, Sequence

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.models.reed import Reed
from app.repositories.reed.reed_repository import ReedRepository


class ReedRepositoryImpl(ReedRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector


    def find_by_gpio_pin_number(self, reed_gpio_pin_number: int) -> Optional[Reed]:
        statement = select(Reed).where(Reed.gpio_pin_number == reed_gpio_pin_number)
        return self.database_connector.get_session().exec(statement).first()


    def create(self, reed: Reed) -> Reed:
        self.database_connector.get_session().add(reed)
        self.database_connector.get_session().commit()
        self.database_connector.get_session().refresh(reed)
        return reed


    def update(self, reed: Reed) -> Optional[Reed]:
        reed_db = self.find_by_gpio_pin_number(reed.gpio_pin_number)
        if reed_db:
            reed_db.default_value_when_closed = reed.default_value_when_closed
            self.database_connector.get_session().commit()
            self.database_connector.get_session().refresh(reed_db)
        return reed_db


    def delete_by_gpio_pin_number(self, reed_gpio_pin_number: int):
        reed = self.find_by_gpio_pin_number(reed_gpio_pin_number)
        if reed:
            self.database_connector.get_session().delete(reed)
            self.database_connector.get_session().commit()
        return reed


    def find_all(self) -> Sequence[Reed]:
        statement = select(Reed)
        return self.database_connector.get_session().exec(statement).all()
