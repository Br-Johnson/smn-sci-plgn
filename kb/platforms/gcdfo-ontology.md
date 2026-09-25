# GCDFO Ontology

- Platform card: [registry/platforms/gcdfo-ontology.json](../../registry/platforms/gcdfo-ontology.json)
- Related skill: [salmon-terms](../../skills/salmon-terms/SKILL.md) (through metasalmonpy's `gcdfo` source adapter)

## Current role

The DFO Salmon Ontology is the DFO-specific semantic/profile layer.

## How the plugin reaches it

Since 2026-09-25 the plugin no longer reads `gcdfo.jsonld` itself. `salmon-terms`
calls metasalmonpy `find_terms(...)` with `gcdfo` in the source list; the
package owns retrieval and ranking. A `gcdfo` hit is reported as DFO
profile-scoped and is never promoted to shared status in chat.

The validator still checks the published JSON-LD surface as a watch surface
(version `0.0.9`, modified 2026-08-16 at last check).

## Current posture

- supported: discovery/search, metadata/schema, provenance/versioning
- partial: entity lookup and identifier-crosswalk support at the modeling level
- unknown: broader verified domain coverage beyond current lookup behavior
- missing: package/export behavior

## Why it matters

It is the right place for DFO-only semantic distinctions, but not the right place for mutable operational crosswalk rows.
