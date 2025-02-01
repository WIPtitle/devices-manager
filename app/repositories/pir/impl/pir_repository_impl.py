from typing import Sequence

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.pir import Pir
from app.models.reed import Reed
from app.repositories.pir.pir_repository import PirRepository


class PirRepositoryImpl(PirRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector


    def find_by_gpio_pin_number(self, pir_gpio_pin_number: int) -> Pir:
        statement = select(Pir).where(Pir.gpio_pin_number == pir_gpio_pin_number)
        session = self.database_connector.get_new_session()
        pir_db = session.exec(statement).first()
        session.close()
        if pir_db is None:
            raise NotFoundException("Pir was not found")

        return pir_db


    def create(self, pir: Pir) -> Pir:
        try:
            self.find_by_gpio_pin_number(pir.gpio_pin_number)
        except NotFoundException:
            statement = select(Reed).where(Reed.gpio_pin_number == pir.gpio_pin_number)

            session = self.database_connector.get_new_session()
            reed_db = session.exec(statement).first()
            if reed_db is not None:
                raise NotFoundException("There is a Reed with the same GPIO pin number")

            session.add(pir)
            session.commit()
            session.refresh(pir)
            session.close()
            return pir
        raise BadRequestException("Pir already exists")


    def update(self, pir: Pir) -> Pir:
        statement = select(Pir).where(Pir.gpio_pin_number == pir.gpio_pin_number)
        session = self.database_connector.get_new_session()
        pir_db = session.exec(statement).first()
        if pir_db is None:
            raise NotFoundException("Pir was not found")

        pir_db.name = pir.name
        session.commit()
        session.refresh(pir_db)
        session.close()
        return pir_db


    def delete_by_gpio_pin_number(self, pir_gpio_pin_number: int) -> Pir:
        statement = select(Pir).where(Pir.gpio_pin_number == pir_gpio_pin_number)
        session = self.database_connector.get_new_session()
        pir_db = session.exec(statement).first()
        if pir_db is None:
            raise NotFoundException("Pir was not found")

        session.delete(pir_db)
        session.commit()
        session.close()
        return pir_db


    def find_all(self) -> Sequence[Pir]:
        statement = select(Pir)
        session = self.database_connector.get_new_session()
        result = session.exec(statement).all()
        session.close()
        return result


    def update_listening(self, pir: Pir, listening: bool):
        statement = select(Pir).where(Pir.gpio_pin_number == pir.gpio_pin_number)
        session = self.database_connector.get_new_session()
        pir_db = session.exec(statement).first()
        if pir_db is None:
            raise NotFoundException("Pir was not found")

        pir_db.listening = listening
        session.commit()
        session.refresh(pir_db)
        session.close()
        return pir_db
