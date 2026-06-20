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

    def test_hyphen_prefixed_commands_are_normalized(self):
        for command in ("detail", "stats", "sources", "fetch", "build"):
            with self.subTest(command=command):
                self.assertEqual([command], normalize_argv([f"-{command}"]))
                self.assertEqual([command], normalize_argv([f"--{command}"]))

    def test_command_words_without_hyphen_are_search_terms(self):
        for term in ("detail", "stats", "sources", "fetch", "build", "search"):
            with self.subTest(term=term):
                self.assertEqual(["search", term], normalize_argv([term]))

    def test_help_is_unchanged(self):
        self.assertEqual(["--help"], normalize_argv(["--help"]))


if __name__ == "__main__":
    unittest.main()
