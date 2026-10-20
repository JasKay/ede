"""PostgreSQL adapter for the shared corpus repository.

Only the repository's fixed SQL templates are translated; user values stay bound.
Connections commit or roll back atomically and are closed after each operation.
"""
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from corpus import Corpus


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return [Row(row) for row in self.cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=None):
        if query == "BEGIN IMMEDIATE":
            query = "SELECT pg_advisory_xact_lock(48239106)"
        return Cursor(self.connection.execute(query.replace("?", "%s"), parameters))

    def executescript(self, script):
        # Schema migration and duplicate checks are serialized across cold starts.
        self.connection.execute("SELECT pg_advisory_xact_lock(48239106)")
        script = script.replace("PRAGMA journal_mode=WAL;", "")
        for statement in script.split(";"):
            if statement.strip():
                self.connection.execute(statement)


class PostgresCorpus(Corpus):
    dialect = "postgres"

    def __init__(self, url):
        self.url = url
        self.initialize()

    @contextmanager
    def connect(self):
        with psycopg.connect(self.url, row_factory=dict_row, connect_timeout=15, prepare_threshold=None) as connection:
            # psycopg batches import writes; SELECT fetches synchronize when needed.
            with connection.pipeline():
                yield Connection(connection)
