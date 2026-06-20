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

### STEPBible TBESG and TBESH

- Project: <https://www.stepbible.org/>
- Local source: existing Lex data package
- License: CC BY 4.0, according to Lex's bundled-data licensing record
- Attribution: STEP Bible; TBESG records retain their individual source label
  such as Abbott-Smith
- Integrity:
  - TBESG SHA-256:
    `67f818251764715a6ce9c85520cef6dfcb7ef870a77dccec8cf0e32ba0d46fae`
  - TBESH SHA-256:
    `b8723804c0a6a710c83239197d23b30239d63d5b024a4842f71106021624f469`

The import preserves lemmas, Strong's and extended Strong's identifiers,
transliterations, morphology codes, English glosses, full definitions, and
record-level source labels. Greek accents and Hebrew points are folded into
additional search aliases without altering displayed headwords.

## Planned importers

- Wiktextract JSONL for multilingual Wiktionary data
- Whitaker's Words for Latin morphology and glosses
- FreeDict TEI dictionaries for European language pairs
- CC-CEDICT for Chinese
- JMdict XML for Japanese
- MorphGNT/Macula Greek and MorphHB as occurrence/syntax layers

Lewis & Short, LSJ, BDB, Korean, Strong's, OpenITI, and Quranic resources
require corpus-specific source and license verification before import.
Several URLs in the initial source list point to organizations, parser tools,
or repositories that no longer exist; those are not silently substituted.
