#!/usr/bin/env python3
"""Create the disposable database used by the README and tests."""

from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "sample.db"

ROWS = [
    ("SQLite", "database", "Embedded relational database engine", "2000-08-17"),
    ("PostgreSQL", "database", "Open source object-relational database", "1996-07-08"),
    ("Redis", "cache", "In-memory data structure server", "2009-05-10"),
    ("Rich", "terminal", "Python library for styled terminal output", "2020-01-01"),
    ("curses", "terminal", "Terminal control interface", "1980-01-01"),
]


def main() -> None:
    if DATABASE.exists():
        DATABASE.unlink()
    with sqlite3.connect(DATABASE) as connection:
        connection.executescript(
            """
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TEXT
            );
            CREATE INDEX idx_items_name ON items(name);
            """
        )
        connection.executemany(
            "INSERT INTO items(name, category, description, created_at) VALUES (?, ?, ?, ?)",
            ROWS,
        )
    print(DATABASE)


if __name__ == "__main__":
    main()

