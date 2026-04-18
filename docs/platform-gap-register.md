# Salmon Domain Parity Gap Register

Purpose: keep a living register of where the salmon domain still lacks the platform maturity or rigor needed to reach parity with the Life Science Research plugin.

Update this file when:
- a skill is added or widened
- an upstream ontology or package version changes
- a source API changes access model, schema, or availability
- a gap closes, worsens, or splits into separate problems
- new tests, fixtures, or golden prompts land

## Parity Dimensions

These are the current parity dimensions taken from the Life Science Research plugin shape:

| Dimension | What parity looks like in practice |
|---|---|
| Breadth of research families | Coverage spans enough source families that major evidence lanes are not structurally missing. |
| Router-led orchestration | Broad questions are scoped into a small number of defensible lanes before retrieval. |
| Canonical entity normalization | Inputs resolve to stable identifiers that survive cross-source joins. |
| Deterministic evidence synthesis | Multi-source workflows produce reproducible ranked outputs, not just chat summaries. |
| Contract-driven maintainability | Skills stay narrow, predictable, and explicit about limits, outputs, and raw-save behavior. |
| Platform affordances | Published artifacts, scripts, docs, and versioned interfaces reduce reliance on ad hoc prompting. |

## Current Gap Matrix

| Priority | Category | Type | Current gap | Why it blocks parity | Current repo state | Next repo move |
|---|---|---|---|---|---|---|
| P0 | Identity and crosswalks | Platform + rigor | No canonical salmon identity graph across `CU`, `SMU`, `DU`, `ESU`, `DPS`, stock, site, hatchery, PIT, and CWT systems. | Cross-source joins remain brittle, so synthesis cannot be trusted at the same level as genetics/variant normalization in the Life Science Research plugin. | `salmon-entity-normalizer-skill` is still a seed alias matcher, not an identity service. | Build a versioned identity graph and crosswalk registry with stable IDs, aliases, lineage, and source provenance. |
| P0 | Semantics and ontology grounding | Rigor | Ontology lookup now exists, but ontology-backed resolution rules are still thin. There is no authoritative mapping layer from real salmon platform fields to `smn` / `gcdfo` terms. | Lookup alone does not make downstream answers semantically safe. The hard part is consistent field, measure, and unit resolution. | `smn-ontology-skill` and `gcdfo-ontology-skill` can now search and fetch terms, but they do not yet drive automated crosswalks. | Add crosswalk fixtures, shared-vs-DFO resolution rules, and package-level semantic QA loops. |
| P0 | Behavioral validation | Rigor | The repo validates structure and Python syntax, but not behavior. | Without fixtures, golden prompts, and regression tests, answers can drift silently as upstream APIs and ontologies change. | `scripts/validate_scaffold.py` only compiles Python and checks manifest/skill presence. | Add fixture-backed tests for each skill plus a small golden-prompt suite for the router and synthesis layer. |
| P0 | Governance-aware access | Platform | Access control is connector-local and mostly environment-variable based. | Gated data sources need explicit policy-aware routing so the agent can distinguish “no data,” “no access,” and “wrong source.” | RMIS and PTAGIS surface auth expectations, but there is no shared governance metadata layer. | Add source-level access metadata, credential-scope notes, and blocked-by-governance routing behavior. |
| P1 | Source-family breadth | Platform | Coverage is still narrow relative to the Life Science Research plugin. | Missing wrappers create structural blind spots in hatchery, harvest, ocean, genetics, and stock-assessment lanes. | Current wrappers: StreamNet, PTAGIS, RMIS, DART, literature, ontology lookup, and `metasalmon`. | Add `CRITFC`, `NOAA SPS`, `NPAFC`, `NuSEDS`, `PacFIN`, and `FINS`, then rank remaining source-family gaps. |
| P1 | Composite workflows | Platform + rigor | The repo routes and fetches, but still lacks durable multi-step workflows that reconcile evidence. | Mature parity requires workflows that convert retrieval into reproducible management or research products. | Router guidance exists; composite salmon workflows do not. | Build stock brief, watershed brief, and mixed-stock management workflows with structured outputs. |
| P1 | Package-first semantic workflows | Platform | `metasalmon` is integrated only through a thin adapter surface. | The strongest current Salmon Data Package engine is not yet fully exposed to the plugin layer. | `metasalmon-skill` now supports runtime, catalog, `sources_for_role()`, `find_terms()`, `fetch_salmon_ontology()`, and `validate_salmon_datapackage()`. | Add safe bridges for package creation, reviewed-package reloads, gap detection, and term-request rendering. |
| P1 | Provenance and evidence weighting | Rigor | Cross-source conflict handling is mostly narrative. | Parity with deterministic life-science synthesis requires explicit scoring, conflict notes, and reproducible output contracts. | Current source skills return summaries but no shared provenance scorecard. | Define a shared evidence-contract schema and use it in future composite workflows. |
| P2 | Change monitoring | Platform + rigor | Skills depend on moving upstream ontologies, package interfaces, and API surfaces. | Without a watchlist, the repo will rot as upstreams evolve. | This register now records the current watch targets. | Add lightweight smoke checks against upstream version surfaces and document drift triggers. |

## Upstream Watchlist

These are the upstream components most likely to force skill updates.

| Component | Current known state | Why it matters | What to watch |
|---|---|---|---|
| `salmon-data-mobilization/salmon-domain-ontology` | Shared ontology, `smn` root currently advertises version `0.0.1`. | Shared semantic layer for cross-organization terms. | Version changes, namespace publication changes, JSON-LD structure, and migration decisions that move terms between namespaces. |
| `dfo-pacific-science/dfo-salmon-ontology` | DFO ontology, published `gcdfo` surface currently advertises version `0.0.8`. | DFO-specific profile layer and boundary decisions against shared `smn`. | Shared-vs-DFO boundary changes, imported shared-term migrations, and published JSON-LD field shape. |
| `dfo-pacific-science/metasalmon` | Installed package version `0.1.2` in this environment. | Strongest current Salmon Data Package implementation and semantic workflow engine. | Exported function signatures, defaults for `find_terms()`, and package-validation behavior. |
| RMIS / RMPC API | Public announcement currently says RMIS `5.0`, effective `Apr 2nd, 2026`. | Coded-wire-tag access is important and auth-sensitive. | Auth model, endpoint set, query syntax, and reporting/API divergence. |

## Current Closure State

Recent closures or partial closures:
- ontology lookup is no longer missing as a skill family
- `metasalmon` is no longer only a note in the README; there is now a thin execution skill
- RMIS is no longer only a recommendation; there is now a real auth-aware scaffold

Still open at parity-blocking severity:
- identity graph
- behavior tests and golden prompts
- governance-aware access model
- deterministic composite workflows
