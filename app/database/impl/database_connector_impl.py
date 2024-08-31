from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import os

from app.database.database_connector import DatabaseConnector
from app.database.impl.base_provider import Base

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self._instance = None

    def get_db(self) -> Session:
        if self._instance is None:
            self._instance = SessionLocal()
        return self._instance
