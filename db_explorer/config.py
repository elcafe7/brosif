"""Configuration loading and schema-independent explorer settings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExplorerConfig:
    database: Path
    table: str
    primary_key: str
    title_column: str
    label_column: str | None
    search_columns: tuple[str, ...]
    list_columns: tuple[str, ...]
    detail_columns: tuple[str, ...]
    order_by: str
    limit: int = 50

    @classmethod
    def load(cls, filename: str | Path) -> "ExplorerConfig":
        path = Path(filename).expanduser().resolve()
        with path.open(encoding="utf-8") as handle:
            data: dict[str, Any] = json.load(handle)

        database = Path(data["database"]).expanduser()
        if not database.is_absolute():
            database = path.parent / database

        title = data["title_column"]
        primary_key = data["primary_key"]
        return cls(
            database=database.resolve(),
            table=data["table"],
            primary_key=primary_key,
            title_column=title,
            label_column=data.get("label_column"),
            search_columns=tuple(data.get("search_columns", [title])),
            list_columns=tuple(data.get("list_columns", [primary_key, title])),
            detail_columns=tuple(
                data.get("detail_columns", data.get("list_columns", [primary_key, title]))
            ),
            order_by=data.get("order_by", title),
            limit=max(1, int(data.get("limit", 50))),
        )

