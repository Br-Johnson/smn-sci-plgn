# metasalmon Skill Capabilities

## Actions

All four run metasalmonpy `v0.5.0` through `scripts/metasalmon_api.py`:

- `runtime`
- `catalog`
- `validate_salmon_datapackage`
- `fetch_salmon_ontology`

`find_terms` and `sources_for_role` moved to the salmon-terms skill on
2026-09-25, so the plugin has one term-search entry point instead of two.

## Not bridged yet

- `create_sdp()` and `read_salmon_datapackage()`
- the 0.5.0 review flow: `review_semantics()`, `accept_suggestion()`,
  `reject_suggestion()`, `apply_sdp_semantics()`, `review_metadata()`, and the
  `set_sdp_*()` setters
- term-gap detection and term-request rendering or submission
- EML, EDH, and KNB publication helpers

These take data frames, interactive review, or credentials, so a JSON-on-stdin
adapter is the wrong shape for them. Run them in Python or R with the user,
following the package documentation.

## Why Python first

metasalmonpy 0.5.0 offers every function the earlier R adapter called, so
running it under uv needs no R installation and changes nothing this skill can
do. The earlier adapter embedded an R runner that chose `find_terms()` sources
itself, which is logic the package owns. R stays documented in `SKILL.md` for
R users and for results that must match an R pipeline exactly.

## Why this skill exists

The packages implement the Salmon Data Package workflows. The plugin exposes
them and does not fork them: a skill calls a package for anything the package
can do.
