# Router Lanes

Use this file when a broad request needs a defensible first routing decision.

## Quick routing table

| Request shape | Start with |
|---|---|
| `What is known about this stock or unit?` | `salmon-entity-normalizer-skill`, then `streamnet-api-skill`, `salmon-literature-skill` |
| `What ontology term matches this salmon concept?` | `smn-ontology-skill`, then `gcdfo-ontology-skill` if the concept is DFO-specific |
| `What does telemetry show?` | `salmon-entity-normalizer-skill`, then `ptagis-skill`, `dart-query-skill` |
| `What does coded-wire-tag / RMIS data show?` | `salmon-entity-normalizer-skill`, then `rmis-skill` |
| `What sources cover this basin or watershed?` | `salmon-entity-normalizer-skill`, then `dart-query-skill`, `streamnet-api-skill` |
| `Find papers or reports on this salmon topic.` | `salmon-literature-skill` |
| `What identifiers or systems does this term belong to?` | `salmon-entity-normalizer-skill` |
| `How do I build or validate a Salmon Data Package?` | `metasalmon-skill` |
| `What is still missing from the salmon platform?` | consult `docs/platform-gap-register.md`, then use source skills only to support the answer |

## Current limitation

The repo does not yet ship:

- a full salmon identity graph
- a CRITFC crosswalk wrapper
- a NuSEDS wrapper
- a hatchery or harvest registry
- fixture-backed behavior tests and golden prompts
- deterministic composite workflows that reconcile evidence across sources

If those are needed, say so clearly instead of pretending the current scaffold can answer them directly.
