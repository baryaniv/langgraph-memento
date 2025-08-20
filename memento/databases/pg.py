import os

from sqlalchemy import create_engine, text
from .. import env


class PG:
    def __init__(self):
        self.uri = env.POSTGRES_URL
        self.engine = create_engine(self.uri, echo=True)
        self.connection = self.engine.connect()

    def execute_query(self, query: str):
        """Execute a SQL query and return the result."""
        with self.connection.begin():
            result = self.connection.execute(statement=text(query))
            return result.fetchall()