# Brosif

**Offline multilingual terminal lexicon** — search across English, Greek, Hebrew, Latin, German, and French from a single database, no internet required.

Brosif combines multiple linguistic corpora (WordNet, biblical texts, classical lexicons, and modern dictionaries) into a 480 MB SQLite database with FTS5 full-text search. It ships with a curses TUI, a Rich-powered CLI, and a lightweight web interface.

---

## Highlights

- **Fully offline** — no API calls, no network dependency after build
- **Multilingual** — English, Biblical Greek, Biblical Hebrew/Aramaic, Classical/Latin, German, French
- **Fast search** — FTS5 with BM25 ranking, 150 ms debounced background queries
- **Grouped results** — identical spellings in the same language collapse into one listing with combined senses
- **Rich detail view** — definitions, examples, synonyms, pronunciation, etymology, morphology, Strong's numbers, and source attribution
- **Three interfaces** — interactive curses TUI, CLI with Rich tables, and a browser-based web UI

---

## Corpora

| Source | Language | Entries | License |
|--------|----------|---------|---------|
| Open English WordNet 2025 | English | 185,129 | CC BY 4.0 / Princeton WN |
| STEPBible TBESG | Biblical Greek | 10,847 | CC BY 4.0 |
| STEPBible TBESH | Biblical Hebrew/Aramaic | 8,723 | CC BY 4.0 |
| Whitaker's Words | Latin | broad | Public domain |
| Lewis & Short | Latin | full | CC BY-SA 4.0 |
| LSJ (Perseus) | Greek (Homer through Koiné) | full | CC BY-SA 4.0 |
| German Wiktionary | German | Wiktextract | CC BY-SA 4.0 |
| FreeDict fra-eng | French | 0.4.1 | GPL 2.0+ |

---

## Install

Requires **Python 3.10+**, **SQLite with FTS5**, and **curl**.

```sh
git clone git@github.com:elcafe7/brosif.git
cd brosif
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Use `scripts/brosif` rather than `.venv/bin/brosif`. The launcher prefers the
project venv and rebuilds it if the interpreter is gone — the usual failure
after a Homebrew Python upgrade, which leaves the venv shebang pointing at a
deleted Cellar path.

```sh
alias brosif="$PWD/scripts/brosif"
```

Fetch WordNet (the only download required for a working install):

```sh
./scripts/brosif -fetch wordnet
```

The database is pre-built in `data/brosif.db`. If you cloned the repo, reassemble
it from the split tarball:

```sh
cat data/brosif.db.tar.part_a* | tar xvf - -C data/
```

To rebuild from scratch, place upstream sources under `data/sources/` and run:

```sh
./scripts/brosif -build
```

See [DATA_SOURCES.md](DATA_SOURCES.md) for provenance, checksums, and licensing details.

---

## Usage

### Interactive TUI

```sh
brosif
```

Type to search, arrow keys to navigate, Enter to open a record, Escape to return or exit. Results are grouped under language headings (English first).

### CLI search

```sh
brosif grace
brosif λόγος
brosif "bank pos:noun"
brosif "run lang:en source:oewn"
brosif amo
brosif "amo source:perseus-lewis-short"
brosif Freiheit
brosif liberté
```

### Filters

Append filter tokens to any search query:

| Filter | Example | Description |
|--------|---------|-------------|
| `lang:<code>` | `lang:grc` | Language prefix (`en`, `grc`, `hbo`, `la`, `de`, `fr`) |
| `pos:<value>` | `pos:noun` | Part of speech |
| `source:<id>` | `source:oewn` | Source identifier |

### Commands

```sh
brosif -detail 123       # view entry by ID
brosif -stats            # show installed corpora
brosif -sources          # show source catalog and roadmap
brosif -fetch wordnet    # download WordNet archive
brosif -build            # rebuild the database
```

### Web UI

```sh
cd web && npm start
# open http://localhost:3847
```

---

## Architecture

```
upstream releases
      │
      ▼
format-specific importer
      │
      ▼
entries + relations + sources ── FTS5 index
      │
      ▼
LexiconAdapter
      │
      ├── curses TUI (color)
      ├── Rich CLI tables
      └── Node.js web server
```

- **`scripts/brosif`** — project launcher (`python -m brosif`) that repairs a stale venv
- **`brosif/`** — lexical schema, source catalog, importers, ranking, CLI
- **`db_explorer/`** — reusable UI engine (curses + Rich)
- **`web/`** — lightweight Node.js HTTP server and single-page frontend
- **`data/`** — generated database and downloaded sources (gitignored)

---

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -v
```

---

## License

Brosif is released under the
[Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/)
license (CC BY-NC 4.0).

Individual data sources carry their own licenses — see
[DATA_SOURCES.md](DATA_SOURCES.md) for full provenance, checksums, and
attribution requirements for each corpus.
