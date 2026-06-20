"""Streaming importers for Perseus Lewis & Short and LSJ TEI P4 files."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET

import beta_code

from ..database import finalize_source, insert_entry, insert_source, strip_marks
from ..sources import source_by_id


SPACE_RE = re.compile(r"\s+")
POS_NAMES = {
    "adj.": "adjective",
    "adv.": "adverb",
    "conj.": "conjunction",
    "interj.": "interjection",
    "n.": "noun",
    "part.": "particle",
    "prep.": "preposition",
    "pron.": "pronoun",
    "v.": "verb",
    "v. a.": "verb",
    "v. dep.": "verb",
    "v. n.": "verb",
}


def compact_text(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip(" ,;\n\t")


def beta_to_greek(value: str) -> str:
    try:
        return unicodedata.normalize("NFC", beta_code.beta_code_to_greek(value))
    except (KeyError, ValueError):
        return value


def _render(element: ET.Element, inherited_language: str = "") -> str:
    language = element.attrib.get("lang", inherited_language)

    def convert(text: str | None, active_language: str) -> str:
        if not text:
            return ""
        return beta_to_greek(text) if active_language in {"greek", "grc"} else text

    parts = [convert(element.text, language)]
    for child in element:
        parts.append(_render(child, language))
        parts.append(convert(child.tail, language))
    return "".join(parts)


def _children_text(entry: ET.Element, tag: str) -> list[str]:
    return [
        compact_text(_render(child))
        for child in entry.findall(tag)
        if compact_text(_render(child))
    ]


def _definition(entry: ET.Element) -> str:
    senses = [
        compact_text(_render(child))
        for child in entry.findall("sense")
        if compact_text(_render(child))
    ]
    if senses:
        return "\n".join(senses)
    excluded = {"orth", "pos", "itype", "gen"}
    parts = [
        compact_text(_render(child))
        for child in entry
        if child.tag not in excluded and compact_text(_render(child))
    ]
    return "\n".join(parts)


def _part_of_speech(entry: ET.Element) -> str:
    values = _children_text(entry, "pos")
    if not values:
        values = _children_text(entry, "gen")
    raw = values[0].casefold() if values else ""
    if raw in {"ὁ", "ἡ", "τό", "το/", "m.", "f.", "n."}:
        return "noun"
    for abbreviation, expanded in POS_NAMES.items():
        if abbreviation in raw:
            return expanded
    return raw or "lexeme"


def import_perseus_tei(
    connection: sqlite3.Connection,
    directory: Path,
    *,
    source_id: str,
    language: str,
    greek_beta_code: bool = False,
    pattern: str = "*.xml",
) -> int:
    source = source_by_id(source_id)
    insert_source(connection, source)
    count = 0
    for path in sorted(directory.glob(pattern)):
        for _, entry in ET.iterparse(path, events=("end",)):
            if entry.tag not in {"entry", "entryFree"}:
                continue
            key = entry.attrib.get("key") or entry.attrib.get("id") or f"{path.stem}:{count}"
            orthographies = _children_text(entry, "orth")
            if greek_beta_code:
                orthographies = [beta_to_greek(value) for value in orthographies]
                key_display = beta_to_greek(key)
            else:
                key_display = key
            headword = next((value for value in orthographies if value), key_display)
            headword = compact_text(headword)
            definition = _definition(entry)
            if not headword or not definition:
                entry.clear()
                continue
            grammar = ", ".join(
                dict.fromkeys(
                    _children_text(entry, "itype") + _children_text(entry, "gen")
                )
            )
            alternate_forms = [
                form for form in orthographies[1:] if form and form != headword
            ]
            aliases = list(
                dict.fromkeys(
                    [
                        key_display,
                        strip_marks(headword),
                        *alternate_forms,
                    ]
                )
            )
            insert_entry(
                connection,
                source_id=source_id,
                source_key=f"{path.stem}:{entry.attrib.get('id', key)}",
                language=language,
                headword=headword,
                part_of_speech=_part_of_speech(entry),
                definition=definition,
                forms=", ".join(value for value in aliases if value),
                metadata=json.dumps(
                    {
                        "key": key,
                        "entry_type": entry.attrib.get("type", ""),
                        "grammar": grammar,
                        "file": path.name,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
            count += 1
            if count % 10_000 == 0:
                connection.commit()
            entry.clear()
    finalize_source(connection, source_id)
    return count
