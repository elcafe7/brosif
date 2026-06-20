"""Build the offline lexicon database."""

from __future__ import annotations

from pathlib import Path

from .database import create_database
from .importers.stepbible import import_stepbible
from .importers.wordnet import import_wordnet


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = PROJECT_ROOT / "data/sources/english-wordnet-2025-json.zip"
DEFAULT_GREEK = PROJECT_ROOT / "data/sources/tbesg-greek.json"
DEFAULT_HEBREW = PROJECT_ROOT / "data/sources/tbesh-hebrew.json"
DEFAULT_DATABASE = PROJECT_ROOT / "data/brosif.db"


def build_database(
    database: Path,
    wordnet_archive: Path,
    greek_path: Path = DEFAULT_GREEK,
    hebrew_path: Path = DEFAULT_HEBREW,
) -> dict[str, int]:
    if not wordnet_archive.exists():
        raise FileNotFoundError(
            f"WordNet archive not found: {wordnet_archive}\n"
            "Run: brosif fetch wordnet"
        )
    for label, path in (("Greek", greek_path), ("Hebrew", hebrew_path)):
        if not path.exists():
            raise FileNotFoundError(f"{label} STEPBible source not found: {path}")
    with create_database(database) as connection:
        return {
            "English": import_wordnet(connection, wordnet_archive),
            "Greek": import_stepbible(connection, greek_path, "stepbible-tbesg", "grc"),
            "Hebrew": import_stepbible(connection, hebrew_path, "stepbible-tbesh", "hbo"),
        }
