# Shared vs DFO Term Boundary

Use `smn` for shared, cross-organization semantics.

Use `gcdfo` for DFO-specific, program-scoped, or policy-scoped semantics.

## Default rule

- if a term is clearly reusable and policy-neutral, prefer `smn`
- if a term is DFO-specific or still boundary-uncertain, keep it in `gcdfo` or a profile bridge first

## What this means for the plugin

- `salmon-terms` keeps `smn` ahead of `gcdfo` in its default source order and reports the `source` of every hit; check the shared layer first for reusable concepts
- DFO-only workflows include `gcdfo` in the `sources` list when shared terms do not exist, and say so in the answer
- a future identity graph can use both ontologies as semantic anchors without collapsing their boundary

## Why this matters

- it prevents local policy terms from polluting the shared layer
- it keeps cross-organization reuse credible
- it avoids treating operational mappings as ontology promotion decisions

Related:
- [SMN ontology](../platforms/smn-ontology.md)
- [GCDFO ontology](../platforms/gcdfo-ontology.md)
- [Ontology vs identity](ontology-vs-identity.md)
