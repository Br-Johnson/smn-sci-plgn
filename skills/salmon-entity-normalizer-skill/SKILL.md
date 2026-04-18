---
name: salmon-entity-normalizer-skill
description: Normalize salmon species names, jurisdiction names, management-unit systems, and common salmon identifier tokens from free text or structured input. Use before multi-source salmon retrieval so routing happens against stable entities, and surface non-authoritative identity hints from the bounded Columbia Basin v0 slice when available.
---

## Operating rules

- Use `scripts/normalize_entities.py` for all current normalization work.
- Treat this as a seed normalizer, not a full salmon identity graph.
- Normalize species and management-unit systems before source selection.
- Preserve ambiguity when the text could map to more than one system.
- Do not invent canonical IDs that are not present in the source text.
- Treat Columbia Basin v0 identity hits as routing hints only, not authoritative identity truth.

## Input

- Read one JSON object from stdin, or a single JSON string containing free text.
- Common fields:
  - `text`
  - `species`
  - `jurisdiction`
  - `entity_ids`
  - `limit`

Examples:

```bash
echo '{"text":"Compare Chinook ESUs in NOAA and DFO CU terminology"}' | python skills/salmon-entity-normalizer-skill/scripts/normalize_entities.py
```

## Output

- `species`
- `jurisdictions`
- `unit_systems`
- `id_tokens`
- `identity_hints`
- `warnings`

See [references/normalization-schema.md](references/normalization-schema.md) for the initial normalization targets.
