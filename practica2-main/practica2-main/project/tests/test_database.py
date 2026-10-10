"""Tests for the SQLite database."""

import sqlite3

from app.database.connection import init_database


def test_database_initialization() -> None:
    """Check that database initialization creates required tables."""
    init_database()

    from app.config.settings import DATABASE_PATH

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        table_names = {row[0] for row in tables}

        assert "users" in table_names
        assert "properties" in table_names
        assert "meters" in table_names
        assert "meter_readings" in table_names
        assert "tariffs" in table_names
        assert "charges" in table_names
        assert "payments" in table_names

    finally:
        connection.close()