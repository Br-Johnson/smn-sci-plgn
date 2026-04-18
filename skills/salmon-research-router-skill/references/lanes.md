# Router Lanes

Use this file when a broad request needs a defensible first routing decision.
After seeding a lane, use [skill-graph-routing.md](skill-graph-routing.md) to expand through dependencies, companion skills, platform cards, and governance constraints.

## Quick routing table

| Lane ID | Request shape | Seed with |
|---|---|---|
| `lane:stock-assessment` | `What is known about this stock or unit?` | `salmon-entity-normalizer-skill`, then `streamnet-api-skill`, `salmon-literature-skill` |
| `lane:ontology-semantic-resolution` | `What ontology term matches this salmon concept?` | `smn-ontology-skill`, then `gcdfo-ontology-skill` if the concept is DFO-specific |
| `lane:telemetry-passage` | `What does telemetry show?` | `salmon-entity-normalizer-skill`, then `ptagis-skill`, `dart-query-skill` |
| `lane:coded-wire-tag-recovery` | `What does coded-wire-tag / RMIS data show?` | `salmon-entity-normalizer-skill`, then `rmis-skill` |
| `lane:watershed-connectivity` | `What sources cover this basin or watershed?` | `salmon-entity-normalizer-skill`, then `dart-query-skill`, `streamnet-api-skill` |
| `lane:literature-reports-dataset-discovery` | `Find papers or reports on this salmon topic.` | `salmon-literature-skill` |
| `lane:hatchery-harvest-management` | `What does harvest or hatchery evidence say?` | `salmon-entity-normalizer-skill`, then `rmis-skill`, `salmon-literature-skill` |
| `lane:genetics-stock-identification` | `What genetics or GSI evidence exists?` | `salmon-literature-skill` |
| `lane:climate-ocean-context` | `What climate or ocean context matters here?` | `salmon-literature-skill` |
| `lane:package-metadata-validation` | `How do I build or validate a Salmon Data Package?` | `metasalmon-skill` |
| special case | `What is still missing from the salmon platform?` | consult `docs/platform-gap-register.md`, then use source skills only to support the answer |

## Current limitation

The repo does not yet ship:

- a full salmon identity graph
- a CRITFC crosswalk wrapper
- a NuSEDS wrapper
- a hatchery or harvest registry
- a fixture-backed graph selector
- fixture-backed behavior tests and golden prompts
- deterministic composite workflows that reconcile evidence across sources

If those are needed, say so clearly instead of pretending the current scaffold can answer them directly.
