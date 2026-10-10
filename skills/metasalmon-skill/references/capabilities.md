# metasalmon Skill Capabilities

## Actions

All seven run metasalmonpy `v0.6.0` through `scripts/metasalmon_api.py`:

- `runtime`
- `catalog`
- `validate_salmon_datapackage`
- `fetch_salmon_ontology`
- `build_review_packet`, which calls `write_semantic_review_packet()`
- `write_assessments`, which writes a harness's judgements as the answer file
  the packet names, copying each slot's identity from the packet and calling
  no package function
- `ingest_assessments`, which calls `ingest_semantic_assessments()`

The last three are the semantic review round trip that the
sdp-semantic-review skill drives.

`find_terms` and `sources_for_role` moved to the salmon-terms skill on
2026-09-25, so the plugin has one term-search entry point instead of two.

## Not bridged yet

- `create_sdp()` and `read_salmon_datapackage()`
- the review console: `review_semantics()`, `accept_suggestion()`,
  `reject_suggestion()`, `apply_sdp_semantics()`, `review_metadata()`, and the
  `set_sdp_*()` setters, where the user confirms what a harness judged
- term-gap detection and term-request rendering or submission
- EML, EDH, and KNB publication helpers

These take data frames, interactive review, or credentials, so a JSON-on-stdin
adapter is the wrong shape for them. Run them in Python or R with the user,
following the package documentation.

## Why Python first

metasalmonpy offers every function the earlier R adapter called, so
running it under uv needs no R installation and changes nothing this skill can
do. The earlier adapter embedded an R runner that chose `find_terms()` sources
itself, which is logic the package owns. R stays documented in `SKILL.md` for
R users and for results that must match an R pipeline exactly.

## Why this skill exists

The packages implement the Salmon Data Package workflows. The plugin exposes
them and does not fork them: a skill calls a package for anything the package
can do.
