"""Database adapter contract used by both CLI and interactive interfaces."""

from __future__ import annotations

from typing import Protocol

from .models import RecordDetail, SearchResult


class ExplorerAdapter(Protocol):
    @property
    def list_columns(self) -> tuple[str, ...]: ...

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]: ...

    def detail(self, key: object) -> RecordDetail | None: ...

    def schema(self) -> list[tuple[str, str, bool]]: ...

