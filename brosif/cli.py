"""Brosif command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

from rich.console import Console
from rich.table import Table

from db_explorer.render import print_detail, print_results
from db_explorer.tui import ExplorerTUI

from .adapter import LexiconAdapter
from .builder import (
    DEFAULT_ARCHIVE,
    DEFAULT_DATABASE,
    DEFAULT_GREEK,
    DEFAULT_HEBREW,
    DEFAULT_WHITAKER,
    DEFAULT_LEWIS_SHORT,
    DEFAULT_LSJ,
    DEFAULT_GERMAN,
    DEFAULT_FRENCH,
    build_database,
)
from .sources import load_catalog

console = Console()
WORDNET_RELEASE_URL = (
    "https://github.com/globalwordnet/english-wordnet/releases/download/"
    "2025-edition/english-wordnet-2025-json.zip"
)
COMMANDS = {"detail", "stats", "sources", "fetch", "build"}


def normalize_argv(argv: list[str]) -> list[str]:
    """Treat bare arguments as searches and hyphen-prefixed names as commands."""
    normalized = list(argv)
    index = 0
    while index < len(normalized):
        argument = normalized[index]
        if argument == "--database":
            index += 2
            continue
        if argument.startswith("--database="):
            index += 1
            continue
        if argument in {"-h", "--help"}:
            return normalized
        command = argument.lstrip("-")
        if argument.startswith("-") and command in COMMANDS:
            normalized[index] = command
            return normalized
        if argument.startswith("-"):
            index += 1
            continue
        normalized.insert(index, "search")
        return normalized
    return normalized


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="brosif",
        description="""
Offline multilingual terminal lexicon with full-text search.

Brosif combines multiple linguistic corpora (WordNet, Biblical texts, classical
classics, and modern dictionaries) into a single searchable database.
        """.strip(),
        epilog=dedent('''
        EXAMPLES:
          brosif                    # Interactive TUI search
          brosif grace              # Search for "grace"
          brosif "bank pos:noun"    # Search with filters
          brosif -detail 123        # View entry by ID
          brosif -stats             # Show installed corpora
          brosif -sources           # Show source roadmap
          brosif -fetch wordnet     # Download WordNet data
          brosif -build             # Rebuild the database

        SEARCH FILTERS:
          lang:<code>     Language code (en, grc, hbo, la, de, fr, etc.)
          pos:<value>     Part of speech (noun, verb, adjective, etc.)
          source:<id>     Source identifier (oewn, grc-tb, heb-tb, etc.)

        For live search with filters, use the interactive TUI (brosif without args).
        ''').strip(),
    )
    result.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Path to lexicon SQLite database file",
    )
    commands = result.add_subparsers(dest="command")
    search = commands.add_parser("search", help=argparse.SUPPRESS)
    search.add_argument("query", nargs="+", help="Search terms and/or filters")
    search.add_argument("--limit", type=int, help="Maximum number of results to show")
    detail = commands.add_parser("detail", help="Display a lexical entry by its ID")
    detail.add_argument("id", type=int, help="Numeric ID of the entry to display")
    commands.add_parser("stats", help="Show statistics about installed corpora")
    commands.add_parser("sources", help="Show the source catalog and roadmap")
    fetch = commands.add_parser("fetch", help="Download upstream data sources")
    fetch.add_argument("source", choices=["wordnet"], help="Data source to download")
    build = commands.add_parser("build", help="Rebuild the lexicon database from sources")
    build.add_argument("--wordnet-archive", type=Path, default=DEFAULT_ARCHIVE,
                      help="Path to WordNet archive file")
    build.add_argument("--greek", type=Path, default=DEFAULT_GREEK,
                      help="Path to Greek lexical data")
    build.add_argument("--hebrew", type=Path, default=DEFAULT_HEBREW,
                      help="Path to Hebrew/Biblical data")
    build.add_argument("--whitaker", type=Path, default=DEFAULT_WHITAKER,
                      help="Path to Whitaker's Words data")
    build.add_argument("--lewis-short", type=Path, default=DEFAULT_LEWIS_SHORT,
                      help="Path to Lewis & Short Latin data")
    build.add_argument("--lsj", type=Path, default=DEFAULT_LSJ,
                      help="Path to LSJ Greek data")
    build.add_argument("--german", type=Path, default=DEFAULT_GERMAN,
                      help="Path to German Wiktionary data")
    build.add_argument("--french", type=Path, default=DEFAULT_FRENCH,
                      help="Path to FreeDict French-English data")
    return result


def _show_sources() -> None:
    table = Table(title="Brosif source catalog")
    for column in ("Status", "Language", "Source", "Purpose"):
        table.add_column(column)
    for item in load_catalog():
        table.add_row(
            item["status"], item["language"], item["name"], item["purpose"]
        )
    console.print(table)


def _show_stats(adapter: LexiconAdapter) -> None:
    table = Table(title=f"Brosif corpora · {adapter.database}")
    for column in ("ID", "Source", "Language", "Version", "Entries"):
        table.add_column(column)
    for row in adapter.stats():
        table.add_row(
            row["id"], row["name"], row["language"], row["version"], str(row["entry_count"])
        )
    console.print(table)


def _fetch_wordnet() -> None:
    DEFAULT_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["curl", "-fL", "--retry", "3", "-o", str(DEFAULT_ARCHIVE), WORDNET_RELEASE_URL],
        check=True,
    )
    console.print(f"Downloaded [cyan]{DEFAULT_ARCHIVE}[/cyan]")


def main() -> None:
    args = parser().parse_args(normalize_argv(sys.argv[1:]))
    try:
        if args.command == "sources":
            _show_sources()
            return
        if args.command == "fetch":
            _fetch_wordnet()
            return
        if args.command == "build":
            counts = build_database(
                args.database,
                args.wordnet_archive,
                args.greek,
                args.hebrew,
                args.whitaker,
                args.lewis_short,
                args.lsj,
                args.german,
                args.french,
            )
            summary = ", ".join(f"{language}: {count:,}" for language, count in counts.items())
            console.print(f"Built [cyan]{args.database}[/cyan] · {summary}")
            return

        adapter = LexiconAdapter(args.database)
        if args.command == "search":
            query = " ".join(args.query)
            print_results(adapter.list_columns, adapter.search(query, args.limit), query)
        elif args.command == "detail":
            detail = adapter.detail(args.id)
            if detail is None:
                raise SystemExit(f"entry not found: {args.id}")
            print_detail(detail)
        elif args.command == "stats":
            _show_stats(adapter)
        elif not sys.stdin.isatty() or not sys.stdout.isatty():
            parser().print_help()
        else:
            ExplorerTUI(adapter, title="Brosif · Offline Lexicon").run()
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
