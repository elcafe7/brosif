"""Source catalog loading."""

from __future__ import annotations

from importlib.resources import files
import json
from typing import Any


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(files("brosif").joinpath("sources.json").read_text("utf-8"))


def source_by_id(source_id: str) -> dict[str, Any]:
    for source in load_catalog():
        if source["id"] == source_id:
            return source
    raise KeyError(source_id)
