"""Build the offline lexicon database."""

from __future__ import annotations

from pathlib import Path

from .database import create_database
from .importers.freedict import import_freedict
from .importers.perseus import import_perseus_tei
from .importers.stepbible import import_stepbible
from .importers.whitaker import import_whitaker
from .importers.wiktextract import import_wiktextract
from .importers.wordnet import import_wordnet


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE = PROJECT_ROOT / "data/sources/english-wordnet-2025-json.zip"
DEFAULT_GREEK = PROJECT_ROOT / "data/sources/tbesg-greek.json"
DEFAULT_HEBREW = PROJECT_ROOT / "data/sources/tbesh-hebrew.json"
DEFAULT_WHITAKER = PROJECT_ROOT / "data/sources/whitakers-words/DICTLINE.GEN"
PERSEUS_ROOT = PROJECT_ROOT / "data/sources/perseus-lexica/CTS_XML_TEI/perseus/pdllex"
DEFAULT_LEWIS_SHORT = PERSEUS_ROOT / "lat/ls"
DEFAULT_LSJ = PERSEUS_ROOT / "grc/lsj"
DEFAULT_GERMAN = PROJECT_ROOT / "data/sources/kaikki.org-dictionary-German.jsonl"
DEFAULT_FRENCH = PROJECT_ROOT / "data/sources/freedict-fra-eng/fra-eng.tei"
DEFAULT_DATABASE = PROJECT_ROOT / "data/brosif.db"


def build_database(
    database: Path,
    wordnet_archive: Path,
    greek_path: Path = DEFAULT_GREEK,
    hebrew_path: Path = DEFAULT_HEBREW,
    whitaker_path: Path = DEFAULT_WHITAKER,
    lewis_short_path: Path = DEFAULT_LEWIS_SHORT,
    lsj_path: Path = DEFAULT_LSJ,
    german_path: Path = DEFAULT_GERMAN,
    french_path: Path = DEFAULT_FRENCH,
) -> dict[str, int]:
    if not wordnet_archive.exists():
        raise FileNotFoundError(
            f"WordNet archive not found: {wordnet_archive}\n"
            "Run: brosif fetch wordnet"
        )
    for label, path in (
        ("Biblical Greek", greek_path),
        ("Hebrew", hebrew_path),
        ("Whitaker", whitaker_path),
        ("Lewis & Short", lewis_short_path),
        ("LSJ", lsj_path),
        ("German", german_path),
        ("French", french_path),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} source not found: {path}")
    with create_database(database) as connection:
        return {
            "English": import_wordnet(connection, wordnet_archive),
            "Biblical Greek": import_stepbible(
                connection, greek_path, "stepbible-tbesg", "grc"
            ),
            "Hebrew": import_stepbible(connection, hebrew_path, "stepbible-tbesh", "hbo"),
            "Latin (Whitaker)": import_whitaker(connection, whitaker_path),
            "Latin (Lewis & Short)": import_perseus_tei(
                connection,
                lewis_short_path,
                source_id="perseus-lewis-short",
                language="la",
                pattern="*eng2.xml",
            ),
            "Ancient Greek (LSJ)": import_perseus_tei(
                connection,
                lsj_path,
                source_id="perseus-lsj",
                language="grc",
                greek_beta_code=True,
            ),
            "German": import_wiktextract(
                connection,
                german_path,
                source_id="wiktextract-de-2026-06",
                language="de",
            ),
            "French": import_freedict(
                connection,
                french_path,
                source_id="freedict-fra-eng",
                language="fr",
            ),
        }
