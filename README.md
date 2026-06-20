# Brosif

Brosif is a fully offline multilingual terminal lexicon built on the reactive
Database Explorer engine. It uses a normalized SQLite schema and FTS5 search,
with one importer per upstream dictionary format.

The current production database contains Open English WordNet 2025:

- 185,129 searchable sense entries
- definitions, examples, synonyms, pronunciations, and inflected forms
- hypernyms, antonyms, meronyms, and other semantic relation targets
- source, version, license, and attribution metadata on every detail record

The source catalog also tracks Wiktionary/Wiktextract, Whitaker's Words,
FreeDict, CC-CEDICT, JMdict, MorphGNT, MorphHB, LSJ, Lewis & Short, BDB, and
other proposed corpora without pretending their formats or licenses are
interchangeable.

## Install and build

Requires Python 3.10 or newer, SQLite with FTS5, `curl`, and a terminal with
curses support.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/brosif fetch wordnet
.venv/bin/brosif build
```

Downloaded sources and generated databases live under `data/` and are not
committed to Git.

## Usage

Launch live search:

```sh
brosif
```

Search or inspect records non-interactively:

```sh
brosif grace
brosif "bank pos:noun"
brosif "run lang:en source:oewn"
brosif detail 123
brosif stats
brosif sources
```

`brosif search <term>` remains available for backward compatibility.

Search filters:

- `lang:<code>` — language code prefix, such as `lang:en`
- `source:<id>` — source ID prefix, such as `source:oewn`
- `pos:<value>` — part-of-speech prefix, such as `pos:noun`

In the TUI, type to search, use arrow keys to select a result, press Enter for
the full lexical record, and press Escape to return or exit. Searches run in
background threads after a 150 ms debounce, and stale responses cannot replace
newer results.

## Architecture

```text
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
      ├── curses live UI
      └── Rich CLI output
```

`db_explorer/` remains the reusable UI engine. `brosif/` owns the lexical
schema, source catalog, importers, ranking, filters, and commands.

See [DATA_SOURCES.md](DATA_SOURCES.md) for provenance and licensing notes.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -v
```
