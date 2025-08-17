import os

from sqlalchemy import create_engine, text
from .. import env


class PG:
    def __init__(self):
        # self.user = os.environ.get("POSTGRES_USER", "postgres")
        # self.password = os.environ["POSTGRES_PASSWORD"]
        # self.host = os.environ.get("POSTGRES_HOSTNAME", "postgres")
        # self.port = os.environ.get("POSTGRES_PORT", 54321)
        # self.database = os.environ.get("POSTGRES_DATABASE", "postgres")
        # auth = f"{self.user}:{self.password}"
        self.uri = env.POSTGRES_URL
        self.engine = create_engine(self.uri, echo=True)
        self.connection = self.engine.connect()

    def execute_query(self, query: str):
        """Execute a SQL query and return the result."""
        with self.connection.begin():
            result = self.connection.execute(text(query))
            return result.fetchall()