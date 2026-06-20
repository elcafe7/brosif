"""Read-only, configuration-driven SQLite adapter."""

from __future__ import annotations

import sqlite3
from typing import Iterable
from urllib.parse import quote

from .config import ExplorerConfig
from .models import RecordDetail, SearchResult


def identifier(name: str) -> str:
    """Quote a SQLite identifier; values are always bound separately."""
    if not isinstance(name, str) or not name:
        raise ValueError("SQL identifiers must be non-empty strings")
    return '"' + name.replace('"', '""') + '"'


class SQLiteAdapter:
    def __init__(self, config: ExplorerConfig):
        self.config = config
        if not config.database.exists():
            raise FileNotFoundError(f"database not found: {config.database}")
        self._validate_columns()

    @property
    def list_columns(self) -> tuple[str, ...]:
        return self.config.list_columns

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{quote(str(self.config.database))}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        return connection

    def _table_columns(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                f"PRAGMA table_info({identifier(self.config.table)})"
            ).fetchall()
        if not rows:
            raise ValueError(f"table or view not found: {self.config.table}")
        return {row["name"] for row in rows}

    def _configured_columns(self) -> Iterable[str]:
        yield self.config.primary_key
        yield self.config.title_column
        if self.config.label_column:
            yield self.config.label_column
        yield from self.config.search_columns
        yield from self.config.list_columns
        yield from self.config.detail_columns
        yield self.config.order_by

    def _validate_columns(self) -> None:
        available = self._table_columns()
        missing = sorted(set(self._configured_columns()) - available)
        if missing:
            raise ValueError(
                f"columns not found in {self.config.table}: {', '.join(missing)}"
            )

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []

        cfg = self.config
        selected = tuple(
            dict.fromkeys(
                (
                    cfg.primary_key,
                    cfg.title_column,
                    *((cfg.label_column,) if cfg.label_column else ()),
                    *cfg.list_columns,
                )
            )
        )
        select_sql = ", ".join(identifier(column) for column in selected)
        predicates = " OR ".join(
            f"LOWER(COALESCE(CAST({identifier(column)} AS TEXT), '')) LIKE ?"
            for column in cfg.search_columns
        )
        sql = (
            f"SELECT {select_sql} FROM {identifier(cfg.table)} "
            f"WHERE {predicates} "
            f"ORDER BY {identifier(cfg.order_by)} LIMIT ?"
        )
        max_rows = min(limit or cfg.limit, 500)
        params = [f"%{query.lower()}%"] * len(cfg.search_columns) + [max_rows]

        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return [
            SearchResult(
                key=row[cfg.primary_key],
                title=str(row[cfg.title_column] or ""),
                label=str(row[cfg.label_column] or "") if cfg.label_column else "",
                values=tuple(row[column] for column in cfg.list_columns),
            )
            for row in rows
        ]

    def detail(self, key: object) -> RecordDetail | None:
        cfg = self.config
        fields = ", ".join(identifier(column) for column in cfg.detail_columns)
        sql = (
            f"SELECT {fields} FROM {identifier(cfg.table)} "
            f"WHERE {identifier(cfg.primary_key)} = ? LIMIT 1"
        )
        with self._connect() as connection:
            row = connection.execute(sql, (key,)).fetchone()
        if row is None:
            return None
        return RecordDetail(
            key=key,
            fields=tuple((column, row[column]) for column in cfg.detail_columns),
        )

    def schema(self) -> list[tuple[str, str, bool]]:
        with self._connect() as connection:
            rows = connection.execute(
                f"PRAGMA table_info({identifier(self.config.table)})"
            ).fetchall()
        return [(row["name"], row["type"] or "", bool(row["notnull"])) for row in rows]

