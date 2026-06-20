from pathlib import Path
import sqlite3
import tempfile
import unittest

from brosif.adapter import LexiconAdapter
from brosif.database import (
    create_database,
    finalize_source,
    insert_entry,
    insert_source,
    strip_marks,
)


SOURCE = {
    "id": "test-source",
    "name": "Test Lexicon",
    "language": "English",
    "version": "1",
    "homepage": "https://example.test",
    "license": "Test",
    "attribution": "Test contributors",
}


class LexiconAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "lexicon.db"
        with create_database(self.database) as connection:
            insert_source(connection, SOURCE)
            insert_entry(
                connection,
                source_id="test-source",
                source_key="grace-1",
                language="en",
                headword="grace",
                part_of_speech="noun",
                definition="unmerited favor",
                synonyms="favor",
                relations=(("hypernym", "gift-1"),),
            )
            insert_entry(
                connection,
                source_id="test-source",
                source_key="grace-1b",
                language="en",
                headword="grace",
                part_of_speech="noun",
                definition="elegance of movement",
            )
            insert_entry(
                connection,
                source_id="test-source",
                source_key="grace-2",
                language="en",
                headword="graceful",
                part_of_speech="adjective",
                definition="showing elegance",
            )
            insert_entry(
                connection,
                source_id="test-source",
                source_key="grace-de",
                language="de",
                headword="grace",
                part_of_speech="noun",
                definition="German test definition",
            )
            finalize_source(connection, "test-source")
        self.adapter = LexiconAdapter(self.database)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_exact_headword_ranks_before_prefix_match(self):
        rows = self.adapter.search("grace")
        english_titles = [row.title for row in rows if row.group == "English"]
        self.assertEqual(["grace", "graceful"], english_titles)
        self.assertEqual("English", rows[0].group)
        self.assertIn("2 senses", rows[0].label)

    def test_results_are_grouped_by_language_with_english_first(self):
        rows = self.adapter.search("grace")
        self.assertEqual("English", rows[0].group)
        self.assertEqual("German", rows[-1].group)

    def test_filters_part_of_speech(self):
        rows = self.adapter.search("grace pos:noun")
        self.assertEqual(
            ["grace"],
            [row.title for row in rows if row.group == "English"],
        )

    def test_searches_definition_and_synonyms(self):
        self.assertEqual("grace", self.adapter.search("unmerited")[0].title)
        self.assertEqual("grace", self.adapter.search("favor")[0].title)

    def test_detail_contains_relation_and_attribution(self):
        detail = self.adapter.detail(self.adapter.search("grace")[0].key)
        self.assertIsNotNone(detail)
        fields = dict(detail.fields)
        self.assertEqual("gift-1", fields["hypernym"])
        self.assertEqual("Test contributors", fields["attribution"])

    def test_database_connection_is_read_only(self):
        with self.adapter._connect() as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM entries")

    def test_script_marks_are_removed_for_search_aliases(self):
        self.assertEqual("λογοσ", strip_marks("λόγος"))
        self.assertEqual("ראשית", strip_marks("רֵאשִׁית"))


if __name__ == "__main__":
    unittest.main()
