"""Streaming importer for FreeDict TEI P5 bilingual dictionaries."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

from ..database import finalize_source, insert_entry, insert_source
from ..sources import source_by_id


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def descendants_text(element: ET.Element, name: str) -> list[str]:
    values = []
    for child in element.iter():
        if local_name(child.tag) == name:
            text = " ".join("".join(child.itertext()).split())
            if text:
                values.append(text)
    return values


def import_freedict(
    connection: sqlite3.Connection,
    path: Path,
    *,
    source_id: str,
    language: str,
) -> int:
    source = source_by_id(source_id)
    insert_source(connection, source)
    count = 0
    for _, entry in ET.iterparse(path, events=("end",)):
        if local_name(entry.tag) != "entry":
            continue
        orthographies = descendants_text(entry, "orth")
        translations = descendants_text(entry, "quote")
        if not orthographies or not translations:
            entry.clear()
            continue
        part_of_speech = next(iter(descendants_text(entry, "pos")), "lexeme")
        gender = ", ".join(dict.fromkeys(descendants_text(entry, "gen")))
        insert_entry(
            connection,
            source_id=source_id,
            source_key=entry.attrib.get("{http://www.w3.org/XML/1998/namespace}id", str(count)),
            language=language,
            headword=orthographies[0],
            part_of_speech=part_of_speech,
            definition="; ".join(dict.fromkeys(translations)),
            forms=", ".join(dict.fromkeys(orthographies)),
            metadata=json.dumps(
                {"gender": gender, "target_language": "en"},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        count += 1
        entry.clear()
    finalize_source(connection, source_id)
    return count
