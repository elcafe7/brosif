"""Build the offline lexicon database."""

from __future__ import annotations

from pathlib import Path

from .database import create_database
from .importers.wordnet import import_wordnet


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = PROJECT_ROOT / "data/sources/english-wordnet-2025-json.zip"
DEFAULT_DATABASE = PROJECT_ROOT / "data/brosif.db"


def build_database(database: Path, wordnet_archive: Path) -> int:
    if not wordnet_archive.exists():
        raise FileNotFoundError(
            f"WordNet archive not found: {wordnet_archive}\n"
            "Run: brosif fetch wordnet"
        )
    with create_database(database) as connection:
        return import_wordnet(connection, wordnet_archive)
