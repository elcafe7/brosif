# Brosif

Brosif is a fully offline multilingual terminal lexicon built on the reactive
Database Explorer engine. It uses a normalized SQLite schema and FTS5 search,
with one importer per upstream dictionary format.

The current production database contains:

- Open English WordNet 2025: 185,129 searchable sense entries
- STEPBible TBESG: 10,847 Biblical Greek lexemes
- STEPBible TBESH: 8,723 Biblical Hebrew/Aramaic lexemes
- Whitaker's Words and Lewis & Short for Latin
- LSJ for Homeric, Attic, Classical, and Hellenistic Greek
- German Wiktionary extracted by Wiktextract
- FreeDict French-English
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
.venv/bin/brosif -fetch wordnet
```

The installed VPS database is already built. A complete rebuild also requires
the ignored source files documented in [DATA_SOURCES.md](DATA_SOURCES.md):
STEPBible TBESG/TBESH, Whitaker's Words, Perseus lexica, the German Kaikki
extract, and FreeDict French-English. After those sources are present:

```sh
.venv/bin/brosif -build
```

Downloaded sources and the generated database live under `data/` and are not
committed to Git because they are large and retain separate upstream licenses.

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
brosif λόγος
brosif logos
brosif G3056
brosif רֵאשִׁית
brosif reshit
brosif H7225
brosif amo
brosif "amo source:perseus-lewis-short"
brosif λόγος source:perseus-lsj
brosif Freiheit
brosif liberté
brosif -detail 123
brosif -stats
brosif -sources
```

Every bare argument is treated as a lookup term. Administrative commands use
a leading hyphen:

- `-detail <id>`
- `-stats`
- `-sources`
- `-fetch wordnet`
- `-build`

Search filters:

- `lang:<code>` — language code prefix, such as `lang:en`
- Biblical Greek uses `lang:grc`; Biblical Hebrew/Aramaic uses `lang:hbo`
- Latin uses `lang:la`, German `lang:de`, and French `lang:fr`
- `source:<id>` — source ID prefix, such as `source:oewn`
- `pos:<value>` — part-of-speech prefix, such as `pos:noun`

In the TUI, type to search, use arrow keys to select a result, press Enter for
the full lexical record, and press Escape to return or exit. Results are grouped
under language headings with English first. Identically spelled entries in the
same language appear once; their parts of speech, sources, and definitions are
combined into that listing. The detail pane exposes every sense and supports
arrow/Page Up/Page Down scrolling. Searches run in background threads after a
150 ms debounce, and stale responses cannot replace newer results.

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
