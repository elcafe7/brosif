# Database Explorer Template

A reusable, read-only terminal interface for searching and inspecting a
SQLite table or view. It is the generalized interaction pattern extracted
from the ICD-11 explorer, without any ICD schema, commands, colors, or data.

The interactive interface behaves like an AJAX search page:

- typing schedules a search after a 150 ms debounce;
- database work runs in background threads;
- stale responses are discarded when a newer query exists;
- results update without pressing Enter;
- arrow keys navigate and Enter opens a record;
- the UI depends on normalized records, not SQLite rows.

## Architecture

```text
keyboard input
    │
    ▼
debounce + generation ID ── discards stale responses
    │
    ▼
ExplorerAdapter protocol
    │
    ├── SQLiteAdapter (included)
    └── PostgreSQL/API/etc. (replaceable)
    │
    ▼
SearchResult / RecordDetail
    │
    ├── curses live UI
    └── Rich non-interactive output
```

The important boundary is `ExplorerAdapter`. The UI only calls:

```python
search(query, limit) -> list[SearchResult]
detail(primary_key) -> RecordDetail | None
schema() -> list[tuple[str, str, bool]]
```

That keeps SQL and schema conventions out of the event loop and renderer.

## Try the sample

Requires Python 3.10 or newer.

```sh
python3 scripts/build_sample_db.py
python3 -m pip install -e .
db-explorer
```

Or run without installing:

```sh
python3 scripts/build_sample_db.py
./db-explorer
```

Non-interactive commands work well in scripts and pipes:

```sh
./db-explorer search terminal
./db-explorer detail 1
./db-explorer schema
```

## Point it at another SQLite database

Copy `explorer.json` and change:

```json
{
  "database": "/absolute/path/to/app.db",
  "table": "customers",
  "primary_key": "id",
  "title_column": "display_name",
  "label_column": "status",
  "search_columns": ["display_name", "email", "notes"],
  "list_columns": ["id", "display_name", "status"],
  "detail_columns": ["id", "display_name", "email", "status", "notes"],
  "order_by": "display_name",
  "limit": 50
}
```

Then use it explicitly:

```sh
db-explorer --config ~/customer-explorer.json
db-explorer --config ~/customer-explorer.json search alice
```

The adapter validates every configured column at startup, quotes identifiers,
binds all search values, and opens SQLite in read-only/query-only mode.

## Generalizable parts

The original domain application mixed four separate concerns. This template
makes each one replaceable:

1. `config.py` describes how domain fields map to generic UI concepts.
2. `sqlite_adapter.py` owns connections, SQL, validation, and row mapping.
3. `models.py` is the contract between data access and presentation.
4. `tui.py` owns input, debounce, stale-response handling, and navigation.
5. `render.py` handles deterministic output when no interactive terminal is
   available.

Domain-specific hierarchy, parent/child traversal, fuzzy scoring, badges, and
detail sections should be implemented in a custom adapter or renderer. They
should not be added to the generic event loop.

## Adapting beyond SQLite

Implement `ExplorerAdapter` in a new module. A remote HTTP or PostgreSQL
adapter can use the same TUI unchanged. For slower backends, retain the
generation ID behavior: cancellation cannot always stop the underlying query,
but stale responses must never replace newer results.

For large SQLite datasets, replace `%term%` scans with an FTS5 virtual table
inside a custom adapter. The UI contract does not change.

## PATH setup

After cloning, add the repository directory to PATH.

macOS Zsh (`~/.zprofile`):

```sh
export PATH="$HOME/db-explorer-template:$PATH"
source ~/.zprofile
```

Linux Bash (`~/.bashrc`):

```sh
export PATH="$HOME/db-explorer-template:$PATH"
source ~/.bashrc
```

Linux Zsh users should put the same export in `~/.zshrc`.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

