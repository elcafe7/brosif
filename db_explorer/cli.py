"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from .config import ExplorerConfig
from .render import print_detail, print_results, print_schema
from .sqlite_adapter import SQLiteAdapter
from .tui import ExplorerTUI


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Explore a configured SQLite table from the terminal"
    )
    result.add_argument(
        "--config", default="explorer.json", help="path to explorer JSON config"
    )
    subcommands = result.add_subparsers(dest="command")

    search = subcommands.add_parser("search", help="search without opening the TUI")
    search.add_argument("query")
    search.add_argument("--limit", type=int)

    detail = subcommands.add_parser("detail", help="show one record by primary key")
    detail.add_argument("key")

    subcommands.add_parser("schema", help="show the configured table schema")
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        config = ExplorerConfig.load(args.config)
        adapter = SQLiteAdapter(config)
        if args.command == "search":
            print_results(
                adapter.list_columns,
                adapter.search(args.query, args.limit),
                args.query,
            )
        elif args.command == "detail":
            record = adapter.detail(args.key)
            if record is None:
                raise SystemExit(f"record not found: {args.key}")
            print_detail(record)
        elif args.command == "schema":
            print_schema(adapter.schema())
        elif not sys.stdin.isatty() or not sys.stdout.isatty():
            parser().print_help()
        else:
            ExplorerTUI(adapter).run()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"configuration error: {error}") from error


if __name__ == "__main__":
    main()

