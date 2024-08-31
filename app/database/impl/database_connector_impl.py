from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import os

from app.database.database_connector import DatabaseConnector


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class DatabaseConnectorImpl(DatabaseConnector):
    def get_db(self) -> Session:

        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

        return None