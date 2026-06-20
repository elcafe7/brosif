"""Brosif command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from rich.console import Console
from rich.table import Table

from db_explorer.render import print_detail, print_results
from db_explorer.tui import ExplorerTUI

from .adapter import LexiconAdapter
from .builder import DEFAULT_ARCHIVE, DEFAULT_DATABASE, build_database
from .sources import load_catalog

console = Console()
WORDNET_RELEASE_URL = (
    "https://github.com/globalwordnet/english-wordnet/releases/download/"
    "2025-edition/english-wordnet-2025-json.zip"
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="brosif", description="Offline multilingual terminal lexicon"
    )
    result.add_argument(
        "--database", type=Path, default=DEFAULT_DATABASE, help="lexicon SQLite file"
    )
    commands = result.add_subparsers(dest="command")
    search = commands.add_parser("search", help="search the lexicon")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int)
    detail = commands.add_parser("detail", help="show an entry by numeric ID")
    detail.add_argument("id", type=int)
    commands.add_parser("stats", help="show installed corpora")
    commands.add_parser("sources", help="show the source roadmap")
    fetch = commands.add_parser("fetch", help="download a source archive")
    fetch.add_argument("source", choices=["wordnet"])
    build = commands.add_parser("build", help="rebuild the lexicon database")
    build.add_argument("--wordnet-archive", type=Path, default=DEFAULT_ARCHIVE)
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
    args = parser().parse_args()
    try:
        if args.command == "sources":
            _show_sources()
            return
        if args.command == "fetch":
            _fetch_wordnet()
            return
        if args.command == "build":
            count = build_database(args.database, args.wordnet_archive)
            console.print(f"Built [cyan]{args.database}[/cyan] with {count:,} entries")
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
