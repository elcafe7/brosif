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

### Whitaker's Words

- Project: <https://github.com/mk270/whitakers-words>
- Revision: `9b11477e53f4adfb17d6f6aa563669dc71e0a680`
- License: the author grants permission for any and all use of the program and
  data, with attribution requested
- Attribution: William A. Whitaker and project contributors

The importer reads the fixed-width `DICTLINE.GEN` source and preserves stems,
part of speech, grammar codes, and English definitions. This is the broad
Classical, ecclesiastical, medieval, legal, philosophical, and medical Latin
layer.

### Lewis & Short and LSJ

- Project: <https://github.com/PerseusDL/lexica>
- Revision: `b5e707bdda2d6c8e0bb6c29657454996b4fb04d7`
- License: CC BY-SA 4.0
- Attribution: Perseus Digital Library, the original lexicon editors, and NEH
  funding as specified in the TEI headers

The supplied Logeion repository URL was unavailable. PerseusDL is the complete
documented upstream source: two Lewis & Short TEI files and 27 LSJ TEI files.
The LSJ importer converts Perseus Beta Code to polytonic Unicode Greek and
preserves accent-insensitive search aliases. It covers Homeric, Attic,
Classical, and Hellenistic Greek.

### German Wiktionary via Wiktextract

- Project: <https://github.com/tatuylonen/wiktextract>
- Extract: <https://kaikki.org/dictionary/German/>
- Extract date: 2026-06-15 from the 2026-06-01 English Wiktionary dump
- License: Wiktionary CC BY-SA 4.0 / GFDL; Wiktextract code MIT
- SHA-256:
  `9779f1f6ae9c7882d1e004e6dcbc1634cbe61405c0e70e253c8c9e72267235b0`

The streaming JSONL importer preserves English glosses, examples,
pronunciations, etymology, and German inflected forms without loading the
one-gigabyte source file into memory.

### FreeDict French-English

- Project: <https://github.com/freedict/fd-dictionaries/tree/master/fra-eng>
- Version: 0.4.1
- License: GNU GPL 2.0 or later
- Attribution: Horst Eyermann, John Darrington, and FreeDict contributors
- SHA-256:
  `de9eb6e5756d994bca9bdb2a91bfc2bb8d8822d3387f5a3b586acc8d42133114`

The importer preserves French headwords, English translations, parts of
speech, alternate forms, and grammatical gender.

## Planned importers

- Wiktextract JSONL for multilingual Wiktionary data
- FreeDict TEI dictionaries for European language pairs
- CC-CEDICT for Chinese
- JMdict XML for Japanese
- MorphGNT/Macula Greek and MorphHB as occurrence/syntax layers

BDB, Korean, OpenITI, and Quranic resources require corpus-specific source and
license verification before import.
Several URLs in the initial source list point to organizations, parser tools,
or repositories that no longer exist; those are not silently substituted.
