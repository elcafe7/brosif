"""UI-facing records that keep database details out of the renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    key: Any
    title: str
    label: str
    values: tuple[Any, ...]


@dataclass(frozen=True)
class RecordDetail:
    key: Any
    fields: tuple[tuple[str, Any], ...]

