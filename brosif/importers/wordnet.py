"""Importer for Open English WordNet release JSON archives."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import zipfile

from ..database import finalize_source, insert_entry, insert_source
from ..sources import source_by_id


POS_NAMES = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective satellite",
    "r": "adverb",
}
NON_RELATION_FIELDS = {
    "definition",
    "example",
    "ili",
    "members",
    "partOfSpeech",
    "source",
    "wikidata",
}


def _text_values(values: list[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, dict) and value.get("text"):
            text = str(value["text"])
            source = value.get("source")
            result.append(f"{text} — {source}" if source else text)
    return result


def _entry_metadata(archive: zipfile.ZipFile) -> tuple[
    dict[tuple[str, str], list[str]], dict[tuple[str, str], list[str]]
]:
    pronunciations: dict[tuple[str, str], list[str]] = defaultdict(list)
    forms: dict[tuple[str, str], list[str]] = defaultdict(list)
    for name in archive.namelist():
        if not name.startswith("entries-") or not name.endswith(".json"):
            continue
        data = json.loads(archive.read(name))
        for lemma, pos_records in data.items():
            for pos, record in pos_records.items():
                key = (lemma, pos)
                pronunciations[key].extend(
                    item["value"]
                    for item in record.get("pronunciation", [])
                    if item.get("value")
                )
                for item in record.get("form", []):
                    if isinstance(item, str):
                        forms[key].append(item)
                    elif item.get("writtenForm"):
                        forms[key].append(item["writtenForm"])
    return pronunciations, forms


def import_wordnet(
    connection: sqlite3.Connection, archive_path: Path
) -> int:
    source = source_by_id("oewn-2025")
    insert_source(connection, source)
    count = 0
    with zipfile.ZipFile(archive_path) as archive:
        pronunciations, forms = _entry_metadata(archive)
        for name in archive.namelist():
            if name.startswith("entries-") or not name.endswith(".json"):
                continue
            if name in {"frames.json"}:
                continue
            data = json.loads(archive.read(name))
            if not isinstance(data, dict):
                continue
            for synset_id, record in data.items():
                members = record.get("members", [])
                definitions = _text_values(record.get("definition", []))
                if not members or not definitions:
                    continue
                pos_code = record.get("partOfSpeech", synset_id.rsplit("-", 1)[-1])
                relation_pairs: list[tuple[str, str]] = []
                for relation, targets in record.items():
                    if relation in NON_RELATION_FIELDS or not isinstance(targets, list):
                        continue
                    relation_pairs.extend(
                        (relation.replace("_", " "), str(target)) for target in targets
                    )
                synonym_text = ", ".join(members)
                for lemma in members:
                    other_members = [item for item in members if item != lemma]
                    insert_entry(
                        connection,
                        source_id=source["id"],
                        source_key=f"{synset_id}:{lemma}",
                        language="en",
                        headword=lemma.replace("_", " "),
                        part_of_speech=POS_NAMES.get(pos_code, pos_code),
                        definition="\n".join(definitions),
                        examples="\n".join(_text_values(record.get("example", []))),
                        synonyms=", ".join(other_members),
                        pronunciation=", ".join(pronunciations.get((lemma, pos_code), [])),
                        forms=", ".join(forms.get((lemma, pos_code), [])),
                        metadata=json.dumps(
                            {
                                "synset": synset_id,
                                "ili": record.get("ili", ""),
                                "members": synonym_text,
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        relations=relation_pairs,
                    )
                    count += 1
            if count and count % 25_000 < 500:
                connection.commit()
    finalize_source(connection, source["id"])
    return count
