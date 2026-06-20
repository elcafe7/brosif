import unittest

from brosif.cli import normalize_argv


class CommandLineTests(unittest.TestCase):
    def test_bare_term_becomes_search(self):
        self.assertEqual(["search", "grace"], normalize_argv(["grace"]))

    def test_multiword_query_becomes_search(self):
        self.assertEqual(
            ["search", "bank", "pos:noun"],
            normalize_argv(["bank", "pos:noun"]),
        )

    def test_database_option_can_precede_query(self):
        self.assertEqual(
            ["--database", "/tmp/lexicon.db", "search", "grace"],
            normalize_argv(["--database", "/tmp/lexicon.db", "grace"]),
        )

    def test_subcommands_are_unchanged(self):
        for command in ("search", "detail", "stats", "sources", "fetch", "build"):
            with self.subTest(command=command):
                self.assertEqual([command], normalize_argv([command]))

    def test_help_is_unchanged(self):
        self.assertEqual(["--help"], normalize_argv(["--help"]))


if __name__ == "__main__":
    unittest.main()
