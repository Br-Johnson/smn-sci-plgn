---
name: smn-ontology-skill
description: Search and fetch terms from the shared Salmon Domain Ontology (`smn`). Use when the user needs shared cross-organization salmon ontology terms, ontology metadata, or a shared semantic lookup before moving to DFO-specific terms.
---

## Operating rules

- Use `scripts/smn_ontology_lookup.py` for all lookups.
- Prefer the shared `smn` layer before the DFO-specific `gcdfo` layer when the concept is cross-organization and policy-neutral.
- Start with `search` when the term is fuzzy.
- Use `get` when the IRI or local name is already known.
- Keep `include_imports` off unless the user explicitly wants imported external terms.

## Published source

This skill reads the published `smn.jsonld` surface.

Default fallbacks:
- `https://salmon-data-mobilization.github.io/salmon-domain-ontology/smn.jsonld`
- `https://raw.githubusercontent.com/salmon-data-mobilization/salmon-domain-ontology/main/docs/smn.jsonld`

Optional override:
- `SMN_ONTOLOGY_JSONLD` may point to a local file or URL.

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
echo '{"action":"meta"}' | python3 skills/smn-ontology-skill/scripts/smn_ontology_lookup.py
echo '{"action":"search","query":"escapement","max_items":5}' | python3 skills/smn-ontology-skill/scripts/smn_ontology_lookup.py
echo '{"action":"get","term":"smn:Escapement"}' | python3 skills/smn-ontology-skill/scripts/smn_ontology_lookup.py
```

Read [references/source-notes.md](references/source-notes.md) when you need the source-of-truth publication notes or shared-vs-DFO boundary reminder.
