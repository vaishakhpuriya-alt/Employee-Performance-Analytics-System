"""
db/connection.py
Manages the SQLite connection lifecycle and provides a query-execution interface
with full exception handling and logging.
"""

import sqlite3
from typing import Generator, Any

from utils import db_logger, log_execution_time, DatabaseConnectionError, QueryExecutionError


class DatabaseConnection:
    """
    Encapsulates an SQLite connection.

    Supports context-manager usage:
        with DatabaseConnection("hr.db") as db:
            rows = db.fetch_all(sql)
    """

    def __init__(self, db_path: str = "hr_analytics.db"):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        db_logger.debug("DatabaseConnection initialised for '%s'", db_path)

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self) -> None:
        try:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row      # dict-like rows
            self._conn.execute("PRAGMA foreign_keys = ON")
            db_logger.info("Connected to database '%s'", self._db_path)
        except sqlite3.Error as exc:
            db_logger.error("Connection failed: %s", exc)
            raise DatabaseConnectionError(str(exc)) from exc

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            db_logger.info("Database connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False          # don't suppress exceptions

    # ── Query helpers ─────────────────────────────────────────────────────────

    def _cursor(self) -> sqlite3.Cursor:
        if self._conn is None:
            raise DatabaseConnectionError("No active connection. Call connect() first.")
        return self._conn.cursor()

    @log_execution_time(db_logger)
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a DML / DDL statement."""
        try:
            cur = self._cursor()
            cur.execute(sql, params)
            self._conn.commit()
            db_logger.debug("Executed: %s | params=%s", sql[:80], params)
            return cur
        except sqlite3.Error as exc:
            db_logger.error("Query execution error: %s", exc)
            raise QueryExecutionError(str(exc)) from exc

    def execute_many(self, sql: str, data: list[tuple]) -> None:
        """Bulk-insert with executemany."""
        try:
            cur = self._cursor()
            cur.executemany(sql, data)
            self._conn.commit()
            db_logger.debug("executemany: %d rows via '%s'", len(data), sql[:60])
        except sqlite3.Error as exc:
            db_logger.error("executemany error: %s", exc)
            raise QueryExecutionError(str(exc)) from exc

    @log_execution_time(db_logger)
    def fetch_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Return all rows at once."""
        try:
            cur = self._cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            db_logger.debug("fetch_all returned %d rows", len(rows))
            return rows
        except sqlite3.Error as exc:
            db_logger.error("fetch_all error: %s", exc)
            raise QueryExecutionError(str(exc)) from exc

    def stream_rows(self, sql: str, params: tuple = (), chunk: int = 100) -> Generator[sqlite3.Row, None, None]:
        """
        Generator – yields rows one at a time (memory-efficient for large results).
        Internally fetches in chunks of `chunk` to avoid holding all data in RAM.
        """
        try:
            cur = self._cursor()
            cur.execute(sql, params)
            db_logger.debug("stream_rows: executing '%s'", sql[:80])
            while True:
                rows = cur.fetchmany(chunk)
                if not rows:
                    break
                for row in rows:
                    yield row
        except sqlite3.Error as exc:
            db_logger.error("stream_rows error: %s", exc)
            raise QueryExecutionError(str(exc)) from exc