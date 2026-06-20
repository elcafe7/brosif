# Data sources

Brosif keeps application code and lexical data separate. Dataset files and
the generated SQLite database are intentionally excluded from Git.

Run `brosif sources` for the machine-readable source roadmap. The catalog
distinguishes installed, planned, research, and blocked sources. A repository
containing parser code is not treated as though it were a redistributable
dictionary.

## Installed

### Open English WordNet 2025

- Project: <https://github.com/globalwordnet/english-wordnet>
- Release artifact: `english-wordnet-2025-json.zip`
- License: Princeton WordNet License for underlying data, with subsequent Open
  English WordNet development under CC BY 4.0
- Attribution: Princeton WordNet and the Open English WordNet team

The importer preserves definitions, examples, synonyms, pronunciations,
inflected forms, synset IDs, ILI IDs, and semantic relation targets.

## Planned importers

- Wiktextract JSONL for multilingual Wiktionary data
- Whitaker's Words for Latin morphology and glosses
- FreeDict TEI dictionaries for European language pairs
- CC-CEDICT for Chinese
- JMdict XML for Japanese
- MorphGNT and MorphHB as morphology/occurrence layers

Lewis & Short, LSJ, BDB, Korean, Strong's, OpenITI, and Quranic resources
require corpus-specific source and license verification before import.
Several URLs in the initial source list point to organizations, parser tools,
or repositories that no longer exist; those are not silently substituted.
