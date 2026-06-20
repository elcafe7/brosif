"""Non-interactive Rich output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import RecordDetail, SearchResult

console = Console()


def print_results(columns: tuple[str, ...], rows: list[SearchResult], query: str) -> None:
    table = Table(title=f"{len(rows)} results for {query!r}")
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(str(value if value is not None else "") for value in row.values))
    console.print(table)


def print_detail(detail: RecordDetail) -> None:
    body = "\n".join(
        f"[bold cyan]{name}[/bold cyan]\n{value if value is not None else ''}"
        for name, value in detail.fields
    )
    console.print(Panel(body, title=f"Record {detail.key}", border_style="cyan"))


def print_schema(rows: list[tuple[str, str, bool]]) -> None:
    table = Table(title="Configured table schema")
    table.add_column("Column")
    table.add_column("Type")
    table.add_column("Required")
    for name, data_type, required in rows:
        table.add_row(name, data_type, "yes" if required else "no")
    console.print(table)

