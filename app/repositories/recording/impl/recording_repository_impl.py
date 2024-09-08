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
        recording_db = self.database_connector.get_session().exec(statement).first()
        if recording_db is None:
            raise NotFoundException("Recording was not found")

        return recording_db


    def create(self, recording: Recording) -> Recording:
        try:
            self.find_by_id(recording.id)
        except NotFoundException:
            self.database_connector.get_session().add(recording)
            self.database_connector.get_session().commit()
            self.database_connector.get_session().refresh(recording)
            return recording
        raise BadRequestException("Recording already exists")


    def set_stopped(self, recording: Recording) -> Recording:
        recording_db = self.find_by_id(recording.id)
        recording_db.is_completed = True
        self.database_connector.get_session().commit()
        self.database_connector.get_session().refresh(recording_db)
        return recording_db


    def delete_by_id(self, rec_id: int) -> Recording:
        recording_db = self.find_by_id(rec_id)
        self.database_connector.get_session().delete(recording_db)
        self.database_connector.get_session().commit()
        return recording_db


    def find_all(self) -> Sequence[Recording]:
        statement = select(Recording)
        return self.database_connector.get_session().exec(statement).all()
