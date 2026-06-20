from pathlib import Path
import sqlite3
import tempfile
import unittest

from db_explorer.config import ExplorerConfig
from db_explorer.sqlite_adapter import SQLiteAdapter, identifier


class SQLiteAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        database = Path(self.tempdir.name) / "test.db"
        with sqlite3.connect(database) as connection:
            connection.executescript(
                """
                CREATE TABLE things (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT,
                    notes TEXT
                );
                INSERT INTO things(name, kind, notes) VALUES
                    ('Alpha', 'letter', 'first'),
                    ('Beta', 'letter', 'second'),
                    ('Hammer', 'tool', 'hits things');
                """
            )
        self.config = ExplorerConfig(
            database=database,
            table="things",
            primary_key="id",
            title_column="name",
            label_column="kind",
            search_columns=("name", "kind", "notes"),
            list_columns=("id", "name", "kind"),
            detail_columns=("id", "name", "kind", "notes"),
            order_by="name",
            limit=50,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_search_normalizes_rows_for_the_ui(self):
        rows = SQLiteAdapter(self.config).search("letter")
        self.assertEqual(["Alpha", "Beta"], [row.title for row in rows])
        self.assertEqual("letter", rows[0].label)

    def test_detail_returns_configured_fields(self):
        detail = SQLiteAdapter(self.config).detail(3)
        self.assertIsNotNone(detail)
        self.assertEqual(("id", 3), detail.fields[0])
        self.assertEqual(("name", "Hammer"), detail.fields[1])

    def test_connection_is_read_only(self):
        adapter = SQLiteAdapter(self.config)
        with adapter._connect() as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM things")

    def test_missing_column_fails_during_startup(self):
        broken = ExplorerConfig(
            **{**self.config.__dict__, "title_column": "missing"}
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            SQLiteAdapter(broken)

    def test_identifier_escaping(self):
        self.assertEqual('"odd""name"', identifier('odd"name'))


if __name__ == "__main__":
    unittest.main()

