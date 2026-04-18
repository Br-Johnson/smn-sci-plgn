---
name: gcdfo-ontology-skill
description: Search and fetch terms from the DFO-specific Salmon Ontology (`gcdfo`). Use when the user needs DFO program, stewardship, or profile-scoped ontology terms after checking whether a shared `smn` term already exists.
---

## Operating rules

- Use `scripts/gcdfo_ontology_lookup.py` for all lookups.
- Prefer `smn` first for shared terms. Use this skill when the concept is clearly DFO-specific or when shared lookup came up short.
- Start with `search` when the term is fuzzy.
- Use `get` when the IRI or local name is already known.
- Keep `include_imports` off unless the user explicitly wants imported or referenced non-DFO terms.

## Published source

This skill reads the published `gcdfo.jsonld` surface.

Default fallbacks:
- `https://dfo-pacific-science.github.io/dfo-salmon-ontology/gcdfo.jsonld`
- `https://raw.githubusercontent.com/dfo-pacific-science/dfo-salmon-ontology/main/docs/gcdfo.jsonld`

Optional override:
- `GCDFO_ONTOLOGY_JSONLD` may point to a local file or URL.

## Input

- Read one JSON object from stdin.
- Supported actions:
  - `meta`
  - `search`
  - `get`
- Optional fields:
  - `query`
  - `term`
  - `include_imports`
  - `max_items`
  - `timeout_sec`
  - `save_raw`
  - `raw_output_path`

Examples:

```bash
echo '{"action":"meta"}' | python3 skills/gcdfo-ontology-skill/scripts/gcdfo_ontology_lookup.py
echo '{"action":"search","query":"conservation unit","max_items":5}' | python3 skills/gcdfo-ontology-skill/scripts/gcdfo_ontology_lookup.py
echo '{"action":"get","term":"gcdfo:ConservationUnit"}' | python3 skills/gcdfo-ontology-skill/scripts/gcdfo_ontology_lookup.py
```

Read [references/source-notes.md](references/source-notes.md) for the current shared-vs-DFO boundary rule.
