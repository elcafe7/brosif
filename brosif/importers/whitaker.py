"""Importer for Whitaker's Words DICTLINE.GEN."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3

from ..database import finalize_source, insert_entry, insert_source
from ..sources import source_by_id


POS_NAMES = {
    "ADJ": "adjective",
    "ADV": "adverb",
    "CONJ": "conjunction",
    "INTERJ": "interjection",
    "N": "noun",
    "NUM": "numeral",
    "PACK": "pronoun",
    "PREP": "preposition",
    "PRON": "pronoun",
    "V": "verb",
    "VPAR": "participle",
}


def import_whitaker(connection: sqlite3.Connection, dictline: Path) -> int:
    source = source_by_id("whitakers-words")
    insert_source(connection, source)
    count = 0
    with dictline.open(encoding="latin-1") as handle:
        for line_number, line in enumerate(handle, 1):
            if len(line) < 111:
                continue
            stems = [
                stem.strip()
                for stem in (line[0:19], line[19:38], line[38:57], line[57:76])
                if stem.strip()
            ]
            grammar = line[76:110].strip()
            definition = line[110:].strip()
            if not stems or not definition:
                continue
            pos_code = grammar.split()[0] if grammar.split() else ""
            headword = stems[0]
            forms = ", ".join(dict.fromkeys(stems))
            insert_entry(
                connection,
                source_id=source["id"],
                source_key=str(line_number),
                language="la",
                headword=headword,
                part_of_speech=POS_NAMES.get(pos_code, pos_code.casefold() or "lexeme"),
                definition=definition,
                forms=forms,
                metadata=json.dumps(
                    {"grammar": grammar, "stems": stems},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
            count += 1
    finalize_source(connection, source["id"])
    return count
