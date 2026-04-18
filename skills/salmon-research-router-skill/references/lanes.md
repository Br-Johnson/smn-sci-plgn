# Router Lanes

Use this file when a broad request needs a defensible first routing decision.
After seeding a lane, use [skill-graph-routing.md](skill-graph-routing.md) to expand through dependencies, companion skills, platform cards, and governance constraints.

## Quick routing table

| Lane ID | Request shape | Seed with |
|---|---|---|
| `lane:stock-assessment` | `What is known about this stock or unit?` | `salmon-entity-normalizer-skill`, then `streamnet-api-skill`, `salmon-literature-skill`, and `noaa-sps-skill` when the request is about ESA recovery or population summaries |
| `lane:crosswalk-harmonization` | `How do these stocks, units, or HUC6 names map across systems?` | `salmon-entity-normalizer-skill`, then `critfc-crosswalk-skill` |
| `lane:ontology-semantic-resolution` | `What ontology term matches this salmon concept?` | `smn-ontology-skill`, then `gcdfo-ontology-skill` if the concept is DFO-specific |
| `lane:telemetry-passage` | `What does telemetry show?` | `salmon-entity-normalizer-skill`, then `ptagis-skill`, `dart-query-skill` |
| `lane:coded-wire-tag-recovery` | `What does coded-wire-tag / RMIS data show?` | `salmon-entity-normalizer-skill`, then `rmis-skill` |
| `lane:watershed-connectivity` | `What sources cover this basin or watershed?` | `salmon-entity-normalizer-skill`, then `dart-query-skill`, `streamnet-api-skill` |
| `lane:literature-reports-dataset-discovery` | `Find papers, reports, datasets, or statistics on this salmon topic.` | `salmon-literature-skill`, then `npafc-skill` when the request is explicitly about catalogues, datasets, downloads, or North Pacific statistics |
| `lane:hatchery-harvest-management` | `What does harvest or hatchery evidence say?` | `salmon-entity-normalizer-skill`, then `rmis-skill`, `salmon-literature-skill` |
| `lane:genetics-stock-identification` | `What genetics or GSI evidence exists?` | `salmon-literature-skill` |
| `lane:climate-ocean-context` | `What climate or ocean context matters here?` | `salmon-literature-skill` |
| `lane:package-metadata-validation` | `How do I build or validate a Salmon Data Package?` | `metasalmon-skill` |
| workflow overlay | `Write me a structured stock brief.` | `salmon-stock-brief-workflow-skill` plus the evidence lanes it depends on |
| special case | `What is still missing from the salmon platform?` | consult `docs/platform-gap-register.md`, then use source skills only to support the answer |

## Current limitation

The repo does not yet ship:

- a full salmon identity graph
- a NuSEDS wrapper
- a hatchery or harvest registry
- full fixture-backed behavior tests and golden prompts for every skill
- deterministic composite workflows beyond the stock-brief scaffold

If those are needed, say so clearly instead of pretending the current scaffold can answer them directly.
