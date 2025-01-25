from typing import Sequence

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.not_found_exception import NotFoundException
from app.models.recording import Recording
from app.repositories.recording.recording_repository import RecordingRepository


class RecordingRepositoryImpl(RecordingRepository):
    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector


    def find_by_id(self, rec_id: int) -> Recording:
        statement = select(Recording).where(Recording.id == rec_id)
        session = self.database_connector.get_new_session()
        recording_db = session.exec(statement).first()
        session.close()
        if recording_db is None:
            raise NotFoundException("Recording was not found")

        return recording_db


    def find_by_name(self, name: str) -> Recording:
        statement = select(Recording).where(Recording.name == name)
        session = self.database_connector.get_new_session()
        recording_db = session.exec(statement).first()
        session.close()
        if recording_db is None:
            raise NotFoundException("Recording was not found")
        return recording_db


    def create(self, recording: Recording) -> Recording:
        try:
            self.find_by_id(recording.id)
        except NotFoundException:
            session = self.database_connector.get_new_session()
            session.add(recording)
            session.commit()
            session.refresh(recording)
            session.close()
            return recording
        raise BadRequestException("Recording already exists")


    def set_stopped(self, recording: Recording) -> Recording:
        statement = select(Recording).where(Recording.id == recording.id)
        session = self.database_connector.get_new_session()
        recording_db = session.exec(statement).first()
        if recording_db is None:
            raise NotFoundException("Recording was not found")

        recording_db.is_completed = True
        session.commit()
        session.refresh(recording_db)
        session.close()
        return recording_db


    def delete_by_id(self, rec_id: int) -> Recording:
        statement = select(Recording).where(Recording.id == rec_id)
        session = self.database_connector.get_new_session()
        recording_db = session.exec(statement).first()
        if recording_db is None:
            raise NotFoundException("Recording was not found")

        session.delete(recording_db)
        session.commit()
        session.close()
        return recording_db


    def find_all(self) -> Sequence[Recording]:
        statement = select(Recording).order_by(Recording.id.desc())
        session = self.database_connector.get_new_session()
        result = session.exec(statement).all()
        session.close()
        return result
