"""Importer for STEPBible TBESG/TBESH JSON lexicons."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3

from ..database import finalize_source, insert_entry, insert_source, strip_marks
from ..sources import source_by_id


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"br", "p", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"p", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(unescape(value))
    text = "".join(parser.parts)
    lines = [re.sub(r"\s+", " ", line).strip(" _") for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def part_of_speech(morph: str) -> str:
    code = morph.split(":", 1)[-1].split("-", 1)[0]
    return {
        "A": "adjective",
        "ADV": "adverb",
        "C": "conjunction",
        "D": "adverb",
        "I": "interjection",
        "N": "noun",
        "P": "preposition",
        "PR": "pronoun",
        "T": "particle",
        "V": "verb",
    }.get(code, code or "lexeme")


def import_stepbible(
    connection: sqlite3.Connection,
    json_path: Path,
    source_id: str,
    language: str,
) -> int:
    source = source_by_id(source_id)
    insert_source(connection, source)
    records = json.loads(json_path.read_text(encoding="utf-8"))
    count = 0
    for key, record in records.items():
        lemma = str(record.get("lemma") or "").strip()
        definition = clean_html(str(record.get("definition") or ""))
        if not lemma or not definition:
            continue
        strongs_id = str(record.get("strongsId") or key)
        extended = str(record.get("extendedStrongs") or strongs_id)
        transliteration = str(record.get("translit") or "").strip()
        gloss = clean_html(str(record.get("gloss") or ""))
        morph = str(record.get("morph") or "")
        compact_transliteration = re.sub(r"[^A-Za-z0-9]+", "", transliteration)
        forms = ", ".join(
            dict.fromkeys(
                value
                for value in (
                    strongs_id,
                    extended,
                    transliteration,
                    compact_transliteration,
                    strip_marks(lemma),
                )
                if value
            )
        )
        insert_entry(
            connection,
            source_id=source_id,
            source_key=key,
            language=language,
            headword=lemma,
            part_of_speech=part_of_speech(morph),
            definition=definition,
            synonyms=gloss,
            pronunciation=transliteration,
            forms=forms,
            metadata=json.dumps(
                {
                    "strongs": strongs_id,
                    "extended_strongs": extended,
                    "morphology": morph,
                    "gloss": gloss,
                    "record_source": record.get("source", ""),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        count += 1
    finalize_source(connection, source_id)
    return count
