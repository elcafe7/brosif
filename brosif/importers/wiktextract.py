"""Streaming importer for Kaikki/Wiktextract JSONL dictionaries."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import sqlite3

from ..database import finalize_source, insert_entry, insert_source
from ..sources import source_by_id


def import_wiktextract(
    connection: sqlite3.Connection,
    path: Path,
    *,
    source_id: str,
    language: str,
) -> int:
    source = source_by_id(source_id)
    insert_source(connection, source)
    opener = gzip.open if path.suffix == ".gz" else open
    count = 0
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            record = json.loads(line)
            word = str(record.get("word") or "").strip()
            pos = str(record.get("pos") or "lexeme")
            senses = record.get("senses") or []
            definitions = []
            examples = []
            for sense in senses:
                definitions.extend(sense.get("glosses") or sense.get("raw_glosses") or [])
                examples.extend(
                    example.get("text", "")
                    for example in sense.get("examples", [])
                    if example.get("text")
                )
            if not word or not definitions:
                continue
            forms = [
                form.get("form", "")
                for form in record.get("forms", [])
                if form.get("form") and "table-tags" not in form.get("tags", [])
            ]
            sounds = [
                sound.get("ipa", "")
                for sound in record.get("sounds", [])
                if sound.get("ipa")
            ]
            insert_entry(
                connection,
                source_id=source_id,
                source_key=f"{line_number}:{word}:{pos}",
                language=language,
                headword=word,
                part_of_speech=pos,
                definition="\n".join(dict.fromkeys(map(str, definitions))),
                examples="\n".join(dict.fromkeys(examples)),
                pronunciation=", ".join(dict.fromkeys(sounds)),
                forms=", ".join(dict.fromkeys(forms)),
                etymology=str(record.get("etymology_text") or ""),
                metadata=json.dumps(
                    {
                        "source_url": record.get("source_url", ""),
                        "categories": record.get("categories", []),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
            count += 1
            if count % 25_000 == 0:
                connection.commit()
    finalize_source(connection, source_id)
    return count
