# Router Lanes

Use this file when a broad request needs a defensible first routing decision.

## Quick routing table

| Request shape | Start with |
|---|---|
| `What is known about this stock or unit?` | `salmon-entity-normalizer-skill`, then `streamnet-api-skill`, `salmon-literature-skill` |
| `What does telemetry show?` | `salmon-entity-normalizer-skill`, then `ptagis-skill`, `dart-query-skill` |
| `What does coded-wire-tag / RMIS data show?` | `salmon-entity-normalizer-skill`, then `rmis-skill` |
| `What sources cover this basin or watershed?` | `salmon-entity-normalizer-skill`, then `dart-query-skill`, `streamnet-api-skill` |
| `Find papers or reports on this salmon topic.` | `salmon-literature-skill` |
| `What identifiers or systems does this term belong to?` | `salmon-entity-normalizer-skill` |

## Current limitation

The repo does not yet ship:

- a full salmon identity graph
- a CRITFC crosswalk wrapper
- a NuSEDS wrapper
- a hatchery or harvest registry
- ontology-browse skills for `smn` and `gcdfo`
- a `metasalmon` execution skill

If those are needed, say so clearly instead of pretending the current scaffold can answer them directly.
