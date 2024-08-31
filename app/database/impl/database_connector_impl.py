from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import os

from app.database.database_connector import DatabaseConnector


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class DatabaseConnectorImpl(DatabaseConnector):
    _instance = None
    def get_db(self) -> Session:
        if self._instance is None:
            self._instance = SessionLocal()
        return self._instance
