"""Read-only lexicon adapter for the generic explorer UI."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

from db_explorer.models import RecordDetail, SearchResult
from .database import strip_marks


FILTER_RE = re.compile(r"^(lang|source|pos):(.+)$", re.IGNORECASE)


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
        params: list[object] = [fts]
        filter_columns = {"lang": "e.language", "source": "e.source_id", "pos": "e.part_of_speech"}
        for key, value in filters.items():
            where.append(f"LOWER({filter_columns[key]}) LIKE ?")
            params.append(f"{value}%")
        params.extend((strip_marks(" ".join(terms)), min(limit or 50, 500)))
        sql = f"""
            SELECT e.id, e.headword, e.part_of_speech, e.language, e.definition,
                   s.name AS source_name,
                   CASE WHEN e.normalized = ? THEN 0 ELSE 1 END AS exact_rank,
                   bm25(entries_fts, 8.0, 2.0, 4.0, 3.0) AS text_rank
            FROM entries_fts
            JOIN entries e ON e.id = entries_fts.rowid
            JOIN sources s ON s.id = e.source_id
            WHERE {' AND '.join(where)}
            ORDER BY exact_rank, text_rank, LENGTH(e.headword), e.headword
            LIMIT ?
        """
        # exact-match parameter belongs after WHERE parameters in the rendered SQL.
        exact = params[-2]
        limit_value = params[-1]
        query_params = [exact, *params[:-2], limit_value]
        with self._connect() as connection:
            rows = connection.execute(sql, query_params).fetchall()
        return [
            SearchResult(
                key=row["id"],
                title=row["headword"],
                label=f"{row['language']} · {row['part_of_speech']}",
                values=(
                    row["headword"],
                    row["part_of_speech"],
                    row["language"],
                    summary(row["definition"]),
                    row["source_name"],
                ),
            )
            for row in rows
        ]

    def detail(self, key: object) -> RecordDetail | None:
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
