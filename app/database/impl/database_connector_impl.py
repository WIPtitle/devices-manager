import json

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
import os

from app.database.database_connector import DatabaseConnector
from app.database.impl.base_provider import Base


# Reads credentials from PG_CREDENTIALS_FILE env, defined inside docker-compose.
def read_pg_credentials(path):
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Postgres credentials file doesn't exist: {path}")

    with open(credentials_file, 'r') as file:
        credentials_map = json.load(file)

    return credentials_map

credentials_file = os.getenv('PG_CREDENTIALS_FILE')
credentials = read_pg_credentials(credentials_file)

engine = create_engine(f"postgresql://{credentials['POSTGRES_USER']}:{credentials['POSTGRES_PASSWORD']}@db:5432/{credentials['POSTGRES_DB']}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self._instance = None

    def get_db(self) -> Session:
        if self._instance is None:
            self._instance = SessionLocal()
        return self._instance
