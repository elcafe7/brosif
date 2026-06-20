"""Lexicon database schema and write API."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterable, Iterator
import unicodedata


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    language TEXT NOT NULL,
    version TEXT,
    homepage TEXT NOT NULL,
    license TEXT NOT NULL,
    attribution TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    entry_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    source_key TEXT NOT NULL,
    language TEXT NOT NULL,
    headword TEXT NOT NULL,
    normalized TEXT NOT NULL,
    part_of_speech TEXT,
    definition TEXT NOT NULL,
    examples TEXT NOT NULL DEFAULT '',
    synonyms TEXT NOT NULL DEFAULT '',
    pronunciation TEXT NOT NULL DEFAULT '',
    etymology TEXT NOT NULL DEFAULT '',
    forms TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source_id, source_key)
);

CREATE TABLE IF NOT EXISTS relations (
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    target_source_key TEXT NOT NULL,
    PRIMARY KEY(entry_id, relation, target_source_key)
);

CREATE INDEX IF NOT EXISTS entries_headword_idx
    ON entries(normalized, language, source_id);
CREATE INDEX IF NOT EXISTS entries_source_idx
    ON entries(source_id);
CREATE INDEX IF NOT EXISTS relations_entry_idx
    ON relations(entry_id);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    headword,
    definition,
    synonyms,
    forms,
    content='entries',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, headword, definition, synonyms, forms)
    VALUES (new.id, new.headword, new.definition, new.synonyms, new.forms);
END;
CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, headword, definition, synonyms, forms)
    VALUES ('delete', old.id, old.headword, old.definition, old.synonyms, old.forms);
END;
CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, headword, definition, synonyms, forms)
    VALUES ('delete', old.id, old.headword, old.definition, old.synonyms, old.forms);
    INSERT INTO entries_fts(rowid, headword, definition, synonyms, forms)
    VALUES (new.id, new.headword, new.definition, new.synonyms, new.forms);
END;
"""


def normalize_headword(value: str) -> str:
    return " ".join(strip_marks(value).replace("_", " ").split())


def strip_marks(value: str) -> str:
    """Remove combining marks for accent/point-insensitive script lookup."""
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    ).casefold()


@contextmanager
def create_database(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        yield connection
        connection.execute("PRAGMA optimize")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def insert_source(connection: sqlite3.Connection, source: dict[str, str]) -> None:
    connection.execute(
        """
        INSERT INTO sources(id, name, language, version, homepage, license, attribution)
        VALUES (:id, :name, :language, :version, :homepage, :license, :attribution)
        """,
        source,
    )


def insert_entry(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    source_key: str,
    language: str,
    headword: str,
    part_of_speech: str,
    definition: str,
    examples: str = "",
    synonyms: str = "",
    pronunciation: str = "",
    etymology: str = "",
    forms: str = "",
    metadata: str = "{}",
    relations: Iterable[tuple[str, str]] = (),
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO entries(
            source_id, source_key, language, headword, normalized,
            part_of_speech, definition, examples, synonyms, pronunciation,
            etymology, forms, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            source_key,
            language,
            headword,
            normalize_headword(headword),
            part_of_speech,
            definition,
            examples,
            synonyms,
            pronunciation,
            etymology,
            forms,
            metadata,
        ),
    )
    entry_id = int(cursor.lastrowid)
    connection.executemany(
        "INSERT OR IGNORE INTO relations(entry_id, relation, target_source_key) "
        "VALUES (?, ?, ?)",
        ((entry_id, relation, target) for relation, target in relations),
    )
    return entry_id


def finalize_source(connection: sqlite3.Connection, source_id: str) -> None:
    connection.execute(
        "UPDATE sources SET entry_count = "
        "(SELECT COUNT(*) FROM entries WHERE source_id = ?) WHERE id = ?",
        (source_id, source_id),
    )
