"""Read-only lexicon adapter for the generic explorer UI."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import quote

from db_explorer.models import RecordDetail, SearchResult
from .database import strip_marks


FILTER_RE = re.compile(r"^(lang|source|pos):(.+)$", re.IGNORECASE)
LANGUAGE_NAMES = {
    "de": "German",
    "en": "English",
    "fr": "French",
    "grc": "Greek",
    "hbo": "Biblical Hebrew / Aramaic",
    "la": "Latin",
}


def summary(value: str, limit: int = 240) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def _fts_query(terms: list[str]) -> str:
    cleaned: list[str] = []
    for term in terms:
        tokens = re.findall(r"[\w'-]+", term, flags=re.UNICODE)
        for token in tokens:
            variants = list(dict.fromkeys((token.casefold(), strip_marks(token))))
            quoted = [f'"{variant.replace(chr(34), chr(34) * 2)}"*' for variant in variants]
            cleaned.append(f"({' OR '.join(quoted)})" if len(quoted) > 1 else quoted[0])
    return " AND ".join(cleaned)


class LexiconAdapter:
    list_columns = ("headword", "part of speech", "language", "definition", "source")

    def __init__(self, database: Path):
        self.database = database.expanduser().resolve()
        if not self.database.exists():
            raise FileNotFoundError(f"lexicon database not found: {self.database}")
        with self._connect() as connection:
            connection.execute("SELECT 1 FROM entries LIMIT 1").fetchone()

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{quote(str(self.database))}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=3)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        return connection

    def _parse_query(self, query: str) -> tuple[list[str], dict[str, str]]:
        terms: list[str] = []
        filters: dict[str, str] = {}
        for token in query.split():
            match = FILTER_RE.match(token)
            if match:
                filters[match.group(1).lower()] = match.group(2).casefold()
            else:
                terms.append(token)
        return terms, filters

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        terms, filters = self._parse_query(query.strip())
        if not terms:
            return []
        fts = _fts_query(terms)
        if not fts:
            return []
        where = ["entries_fts MATCH ?"]
        filter_params: list[object] = [fts]
        filter_columns = {"lang": "e.language", "source": "e.source_id", "pos": "e.part_of_speech"}
        for key, value in filters.items():
            where.append(f"LOWER({filter_columns[key]}) LIKE ?")
            filter_params.append(f"{value}%")
        group_limit = min(limit or 50, 500)
        row_limit = min(max(group_limit * 10, 250), 2_500)
        exact = strip_marks(" ".join(terms))
        sql = f"""
            SELECT e.id, e.headword, e.part_of_speech, e.language, e.definition,
                   s.name AS source_name,
                   CASE WHEN e.normalized = ? THEN 0 ELSE 1 END AS exact_rank,
                   bm25(entries_fts, 8.0, 2.0, 4.0, 3.0) AS text_rank
            FROM entries_fts
            JOIN entries e ON e.id = entries_fts.rowid
            JOIN sources s ON s.id = e.source_id
            WHERE {' AND '.join(where)} AND e.language = ?
            ORDER BY exact_rank, text_rank, LENGTH(e.headword), e.headword
            LIMIT ?
        """
        with self._connect() as connection:
            language_sql = "SELECT DISTINCT language FROM entries"
            language_params: tuple[object, ...] = ()
            if "lang" in filters:
                language_sql += " WHERE LOWER(language) LIKE ?"
                language_params = (f"{filters['lang']}%",)
            languages = [
                row[0]
                for row in connection.execute(
                    f"{language_sql} ORDER BY CASE WHEN language = 'en' THEN 0 ELSE 1 END, language",
                    language_params,
                )
            ]
            rows = []
            for language in languages:
                rows.extend(
                    connection.execute(
                        sql,
                        [exact, *filter_params, language, row_limit],
                    ).fetchall()
                )
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            group_key = (row["language"], strip_marks(row["headword"]))
            item = grouped.setdefault(
                group_key,
                {
                    "language": row["language"],
                    "headword": row["headword"],
                    "parts": [],
                    "definitions": [],
                    "sources": [],
                    "rank": (row["exact_rank"], row["text_rank"], len(row["headword"])),
                },
            )
            if row["part_of_speech"] not in item["parts"]:
                item["parts"].append(row["part_of_speech"])
            if row["definition"] not in item["definitions"]:
                item["definitions"].append(row["definition"])
            if row["source_name"] not in item["sources"]:
                item["sources"].append(row["source_name"])

        by_language: dict[str, list[dict[str, Any]]] = {}
        for item in grouped.values():
            by_language.setdefault(item["language"], []).append(item)
        for items in by_language.values():
            items.sort(key=lambda item: (item["rank"], strip_marks(item["headword"])))

        selected: list[dict[str, Any]] = []
        if len(by_language) <= 1:
            selected = next(iter(by_language.values()), [])[:group_limit]
        else:
            english = by_language.pop("en", [])
            english_quota = min(len(english), max(1, group_limit // 2))
            selected.extend(english[:english_quota])
            remaining = group_limit - len(selected)
            language_keys = sorted(
                by_language,
                key=lambda code: LANGUAGE_NAMES.get(code, code).casefold(),
            )
            offsets = {code: 0 for code in language_keys}
            while remaining and language_keys:
                next_keys = []
                for code in language_keys:
                    offset = offsets[code]
                    if offset < len(by_language[code]) and remaining:
                        selected.append(by_language[code][offset])
                        offsets[code] += 1
                        remaining -= 1
                    if offsets[code] < len(by_language[code]):
                        next_keys.append(code)
                language_keys = next_keys
            if remaining:
                selected.extend(english[english_quota : english_quota + remaining])

        ordered = sorted(
            selected,
            key=lambda item: (
                0 if item["language"] == "en" else 1,
                LANGUAGE_NAMES.get(item["language"], item["language"]).casefold(),
                item["rank"],
                strip_marks(item["headword"]),
            ),
        )
        results = []
        for item in ordered:
            sense_count = len(item["definitions"])
            definition_preview = " • ".join(
                summary(definition, 110) for definition in item["definitions"][:3]
            )
            if sense_count > 3:
                definition_preview += f" • +{sense_count - 3} more"
            parts = ", ".join(item["parts"])
            sources = ", ".join(item["sources"])
            language_name = LANGUAGE_NAMES.get(item["language"], item["language"])
            results.append(
                SearchResult(
                    key=("lexeme", item["language"], strip_marks(item["headword"])),
                    title=item["headword"],
                    label=f"{parts} · {sense_count} sense{'s' if sense_count != 1 else ''}",
                    values=(
                        item["headword"],
                        parts,
                        language_name,
                        definition_preview,
                        sources,
                    ),
                    group=language_name,
                )
            )
        return results

    def detail(self, key: object) -> RecordDetail | None:
        if (
            isinstance(key, tuple)
            and len(key) == 3
            and key[0] == "lexeme"
        ):
            return self._group_detail(str(key[1]), str(key[2]))
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT e.*, s.name AS source_name, s.version, s.homepage,
                       s.license, s.attribution
                FROM entries e JOIN sources s ON s.id = e.source_id
                WHERE e.id = ?
                """,
                (key,),
            ).fetchone()
            if row is None:
                return None
            relation_rows = connection.execute(
                """
                SELECT relation, GROUP_CONCAT(target_source_key, ', ') AS targets
                FROM relations WHERE entry_id = ?
                GROUP BY relation ORDER BY relation
                """,
                (key,),
            ).fetchall()
        metadata = json.loads(row["metadata"])
        fields: list[tuple[str, object]] = [
            ("headword", row["headword"]),
            ("language", row["language"]),
            ("part of speech", row["part_of_speech"]),
            ("definition", row["definition"]),
        ]
        for label, column in (
            ("examples", "examples"),
            ("synonyms", "synonyms"),
            ("pronunciation", "pronunciation"),
            ("forms", "forms"),
            ("etymology", "etymology"),
        ):
            if row[column]:
                fields.append((label, row[column]))
        if metadata.get("synset"):
            fields.append(("synset", metadata["synset"]))
        for key, label in (
            ("strongs", "Strong's"),
            ("extended_strongs", "extended Strong's"),
            ("gloss", "gloss"),
            ("morphology", "morphology"),
            ("grammar", "grammar"),
            ("gender", "gender"),
            ("target_language", "target language"),
        ):
            if metadata.get(key):
                fields.append((label, metadata[key]))
        for relation in relation_rows:
            fields.append((relation["relation"], relation["targets"]))
        fields.extend(
            [
                ("source", f"{row['source_name']} {row['version']}"),
                ("license", row["license"]),
                ("homepage", row["homepage"]),
                ("attribution", row["attribution"]),
            ]
        )
        return RecordDetail(key=key, fields=tuple(fields))

    def _group_detail(self, language: str, normalized: str) -> RecordDetail | None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.*, s.name AS source_name, s.version, s.homepage,
                       s.license, s.attribution
                FROM entries e JOIN sources s ON s.id = e.source_id
                WHERE e.language = ? AND e.normalized = ?
                ORDER BY e.part_of_speech, s.name, e.id
                """,
                (language, normalized),
            ).fetchall()
            relation_rows = connection.execute(
                """
                SELECT r.relation, GROUP_CONCAT(DISTINCT r.target_source_key) AS targets
                FROM relations r
                JOIN entries e ON e.id = r.entry_id
                WHERE e.language = ? AND e.normalized = ?
                GROUP BY r.relation ORDER BY r.relation
                """,
                (language, normalized),
            ).fetchall()
        if not rows:
            return None
        headword = rows[0]["headword"]
        sources = list(dict.fromkeys(row["source_name"] for row in rows))
        licenses = list(dict.fromkeys(row["license"] for row in rows))
        attributions = list(dict.fromkeys(row["attribution"] for row in rows))
        fields: list[tuple[str, object]] = [
            ("headword", headword),
            ("language", LANGUAGE_NAMES.get(language, language)),
            ("senses", len(rows)),
            ("sources", ", ".join(sources)),
            ("licenses", ", ".join(licenses)),
            ("attribution", "\n".join(attributions)),
        ]
        for index, row in enumerate(rows, 1):
            metadata = json.loads(row["metadata"])
            heading = f"sense {index} · {row['part_of_speech']} · {row['source_name']}"
            body = row["definition"]
            extras = []
            if row["synonyms"]:
                extras.append(f"Synonyms/gloss: {row['synonyms']}")
            if row["pronunciation"]:
                extras.append(f"Pronunciation: {row['pronunciation']}")
            if row["examples"]:
                extras.append(f"Examples:\n{row['examples']}")
            if metadata.get("grammar"):
                extras.append(f"Grammar: {metadata['grammar']}")
            if metadata.get("strongs"):
                extras.append(f"Strong's: {metadata['strongs']}")
            if extras:
                body = f"{body}\n\n" + "\n".join(extras)
            fields.append((heading, body))
            fields.append(
                (
                    f"source {index}",
                    f"{row['source_name']} {row['version']}\n"
                    f"License: {row['license']}\n"
                    f"Attribution: {row['attribution']}\n"
                    f"{row['homepage']}",
                )
            )
        for relation in relation_rows:
            fields.append((relation["relation"], relation["targets"]))
        return RecordDetail(
            key=f"{LANGUAGE_NAMES.get(language, language)} · {headword}",
            fields=tuple(fields),
        )

    def stats(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT s.id, s.name, s.language, s.version, s.entry_count
                FROM sources s ORDER BY s.name
                """
            ).fetchall()

    def schema(self) -> list[tuple[str, str, bool]]:
        with self._connect() as connection:
            rows = connection.execute("PRAGMA table_info(entries)").fetchall()
        return [(row["name"], row["type"], bool(row["notnull"])) for row in rows]
