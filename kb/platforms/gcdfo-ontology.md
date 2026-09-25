# GCDFO Ontology

- Platform card: [registry/platforms/gcdfo-ontology.json](../../registry/platforms/gcdfo-ontology.json)
- Related skill: [salmon-terms](../../skills/salmon-terms/SKILL.md), which searches gcdfo through metasalmonpy's `find_terms()`

## Current role

The DFO Salmon Ontology is the DFO-specific semantic/profile layer.

## Current posture

- supported: discovery/search, metadata/schema, provenance/versioning
- partial: entity lookup and identifier-crosswalk support at the modeling level
- unknown: broader verified domain coverage beyond term search
- missing: package/export behavior

## Why it matters

It is the right place for DFO-only semantic distinctions, but not the right place for mutable operational crosswalk rows.
