import json
import os

from sqlmodel import Session, create_engine

from app.database.database_connector import DatabaseConnector


# Reads credentials from PG_CREDENTIALS_FILE env, defined inside docker-compose.
def read_pg_credentials(path):
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Postgres credentials file doesn't exist: {path}")

    with open(path, 'r') as file:
        credentials_map = json.load(file)

    return credentials_map

class DatabaseConnectorImpl(DatabaseConnector):
    def __init__(self):
        credentials_file = os.getenv('PG_CREDENTIALS_FILE')
        credentials = read_pg_credentials(credentials_file)

        self.engine = create_engine(
            f"postgresql://{credentials['POSTGRES_USER']}:{credentials['POSTGRES_PASSWORD']}@db:5432/{credentials['POSTGRES_DB']}",
            echo=True)

    def get_session(self) -> Session:
        with Session(self.engine) as session:
            return session
