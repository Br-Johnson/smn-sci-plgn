# SMN Ontology

- Platform card: [registry/platforms/smn-ontology.json](../../registry/platforms/smn-ontology.json)
- Related skill: [salmon-terms](../../skills/salmon-terms/SKILL.md) (through metasalmonpy's `smn` source adapter)

## Current role

The shared Salmon Domain Ontology is the semantic layer for cross-organization salmon concepts.

## How the plugin reaches it

Since 2026-09-25 the plugin no longer reads `smn.jsonld` itself. `salmon-terms`
calls metasalmonpy `find_terms(..., sources=["smn", ...])`, and the package
owns retrieval, ranking, and query expansion. Coverage therefore follows the
pinned metasalmonpy release, not this repository.

The validator still checks the published JSON-LD surface as a watch surface
(version `0.0.3`, modified 2026-08-14 at last check) so drift stays visible.

## Current posture

- supported: discovery/search, metadata/schema, provenance/versioning
- partial: entity lookup and identifier-crosswalk support at the modeling level
- unknown: several domain sub-areas are not yet maintained as verified coverage claims
- missing: package/export behavior

## Why it matters

This ontology helps define what identity and crosswalk assertions mean, but it does not replace the identity graph itself.
