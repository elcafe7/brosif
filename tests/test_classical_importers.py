from pathlib import Path
import sqlite3
import tempfile
import unittest

from brosif.database import create_database
from brosif.importers.freedict import import_freedict
from brosif.importers.perseus import beta_to_greek, import_perseus_tei
from brosif.importers.whitaker import import_whitaker
from brosif.importers.wiktextract import import_wiktextract


class ClassicalImporterTests(unittest.TestCase):
    def test_beta_code_conversion(self):
        self.assertEqual("λόγος", beta_to_greek("lo/gos"))
        self.assertEqual("Ἀθήνη", beta_to_greek("*a)qh/nh"))

    def test_whitaker_fixed_width_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "DICTLINE.GEN"
            source.write_text(
                f"{'am':<19}{'am':<19}{'amav':<19}{'amat':<19}"
                f"{'V      1 1':<34}love; like; be fond of;\n",
                encoding="latin-1",
            )
            database = root / "test.db"
            with create_database(database) as connection:
                count = import_whitaker(connection, source)
            self.assertEqual(1, count)
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    ("am", "verb"),
                    connection.execute(
                        "SELECT headword, part_of_speech FROM entries"
                    ).fetchone(),
                )

    def test_perseus_lsj_import_converts_headword(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "lsj"
            source.mkdir()
            (source / "sample.xml").write_text(
                """<TEI.2><text><body>
                <entryFree id="n1" key="lo/gos">
                  <orth lang="greek">lo/gos</orth>
                  <pos>noun</pos>
                  <sense>word, speech, account</sense>
                </entryFree>
                </body></text></TEI.2>""",
                encoding="utf-8",
            )
            database = root / "test.db"
            with create_database(database) as connection:
                count = import_perseus_tei(
                    connection,
                    source,
                    source_id="perseus-lsj",
                    language="grc",
                    greek_beta_code=True,
                )
            self.assertEqual(1, count)
            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    "λόγος",
                    connection.execute("SELECT headword FROM entries").fetchone()[0],
                )
                self.assertEqual(
                    "noun",
                    connection.execute(
                        "SELECT part_of_speech FROM entries"
                    ).fetchone()[0],
                )

    def test_freedict_translation_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fra-eng.tei"
            source.write_text(
                """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
                <entry xml:id="chat"><form><orth>chat</orth></form>
                <gramGrp><pos>n</pos><gen>masc</gen></gramGrp>
                <sense><cit type="trans"><quote>cat</quote></cit></sense></entry>
                </body></text></TEI>""",
                encoding="utf-8",
            )
            database = root / "test.db"
            with create_database(database) as connection:
                count = import_freedict(
                    connection,
                    source,
                    source_id="freedict-fra-eng",
                    language="fr",
                )
            self.assertEqual(1, count)

    def test_wiktextract_jsonl_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "de.jsonl"
            source.write_text(
                '{"word":"frei","pos":"adj","senses":[{"glosses":["free"]}],'
                '"sounds":[{"ipa":"/fʁaɪ̯/"}],"forms":[{"form":"freier"}]}\n',
                encoding="utf-8",
            )
            database = root / "test.db"
            with create_database(database) as connection:
                count = import_wiktextract(
                    connection,
                    source,
                    source_id="wiktextract-de-2026-06",
                    language="de",
                )
            self.assertEqual(1, count)


if __name__ == "__main__":
    unittest.main()
