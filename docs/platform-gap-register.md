# Salmon Domain Parity Gap Register

Purpose: keep a living register of where the salmon domain still lacks the platform maturity or rigor needed to reach parity with the Life Science Research plugin.

Detailed per-platform truth now lives in:
- [registry/platforms/](../registry/platforms/)
- [kb/platforms/](../kb/platforms/)

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

## Platform Capability Categories Referenced

The per-platform registry uses these normalized categories:

- `discovery_search`
- `metadata_schema`
- `entity_lookup`
- `identifier_crosswalks`
- `abundance_assessment`
- `telemetry_passage`
- `hatchery`
- `harvest_fishery`
- `genetics_gsi`
- `package_metadata_export`
- `provenance_versioning`
- `bulk_access_api_ergonomics`

## Current Gap Matrix

| Priority | Category | Type | Current gap | Why it blocks parity | Current repo state | Next repo move |
|---|---|---|---|---|---|---|
| P0 | Identity and crosswalks | Platform + rigor | No authoritative salmon identity graph spans `CU`, `SMU`, `DU`, `ESU`, `DPS`, stock, site, hatchery, PIT, and CWT systems. | Cross-source joins remain brittle, so synthesis cannot be trusted at the same level as genetics/variant normalization in the Life Science Research plugin. | `salmon-entity-normalizer-skill` still emits routing hints rather than production truth, but the repo now has `registry/identity-record.schema.json`, `registry/identity/columbia-basin-v0.json`, and bounded Columbia Basin identity hints. | Turn the bounded slice into a reviewed, versioned crosswalk registry with stable IDs, aliases, lineage, source provenance, and broader regional coverage. |
| P0 | Semantics and ontology grounding | Rigor | Ontology lookup now exists, but ontology-backed resolution rules are still thin. There is no authoritative mapping layer from real salmon platform fields to `smn` / `gcdfo` terms. | Lookup alone does not make downstream answers semantically safe. The hard part is consistent field, measure, and unit resolution. | `smn-ontology-skill` and `gcdfo-ontology-skill` can search and fetch terms, and the wiki now records the ontology-vs-identity boundary, but automated crosswalk resolution is still absent. | Add crosswalk fixtures, shared-vs-DFO resolution rules, and package-level semantic QA loops. |
| P0 | Behavioral validation | Rigor | The repo now has selector fixtures and CI, but not broad answer-quality regression coverage. | Without broader fixtures and golden prompts, retrieval and synthesis can still drift silently as upstream APIs and ontologies change. | `scripts/validate_scaffold.py` validates structure and watch surfaces, `.github/workflows/scaffold-validation.yml` runs validation plus selector tests, and `tests/fixtures/skill_graph_selector_cases.json` covers route selection, but per-skill and synthesis-quality regression is still absent. | Add fixture-backed smoke tests for each source skill plus a small golden-prompt suite for router and synthesis outputs. |
| P0 | Governance-aware access | Platform | Access control is now normalized, but it is still only a thin policy layer. | Gated data sources need explicit policy-aware routing so the agent can distinguish “no data,” “no access,” and “wrong source.” | Platform cards now carry `access_tier`, and the executable selector can block credentialed routes for no-auth requests, but runtime policy remains heuristic and route-specific. | Extend access handling from `access_tier` into richer credential scope, project-gating, and partial-public policy rules. |
| P1 | Source-family breadth | Platform | Coverage is broader, but still not yet near Life Science Research plugin breadth. | Missing wrappers still create structural blind spots in hatchery, harvest, ocean, genetics, and stock-assessment lanes. | Current wrappers now include StreamNet, PTAGIS, RMIS, DART, literature, ontology lookup, `metasalmon`, CRITFC crosswalk, NOAA SPS, and NPAFC. | Add `NuSEDS`, `PacFIN`, and `FINS`, then rank the remaining source-family gaps by join value rather than endpoint count. |
| P1 | Composite workflows | Platform + rigor | The repo now has a stock-brief scaffold, but not durable multi-step workflows with robust reconciliation. | Mature parity requires workflows that convert retrieval into reproducible management or research products. | `salmon-stock-brief-workflow-skill` defines a fixed contract and validation helper, but it is still scaffold-level and not yet a full orchestrated workflow engine. | Extend from stock brief into watershed-risk and mixed-stock management workflows with shared evidence contracts. |
| P1 | Package-first semantic workflows | Platform | `metasalmon` is integrated only through a thin adapter surface. | The strongest current Salmon Data Package engine is not yet fully exposed to the plugin layer. | `metasalmon-skill` now supports runtime, catalog, `sources_for_role()`, `find_terms()`, `fetch_salmon_ontology()`, and `validate_salmon_datapackage()`. | Add safe bridges for package creation, reviewed-package reloads, gap detection, and term-request rendering. |
| P1 | Provenance and evidence weighting | Rigor | Cross-source conflict handling is mostly narrative. | Parity with deterministic life-science synthesis requires explicit scoring, conflict notes, and reproducible output contracts. | Current source skills return summaries but no shared provenance scorecard. | Define a shared evidence-contract schema and use it in future composite workflows. |
| P2 | Skill-graph routing maturity | Rigor + maintainability | A typed skill graph and executable selector now exist, but lane seeding, subgraph scoring, and availability-aware expansion are still heuristic. | Graph topology now drives real decisions, so parity depends on ranking quality and drift detection when the route behavior changes. | `registry/skill-graph.json` models skill, platform, lane, and governance nodes; `scripts/skill_graph_selector.py` selects routed skill sets; and the selector is fixture-backed. | Extend the selector toward capability-aware ranking, richer auth-state pruning, and golden routing cases tied directly to graph changes. |
| P2 | Change monitoring | Platform + rigor | Skills depend on moving upstream ontologies, package interfaces, and API surfaces. | Without a watchlist, the repo will rot as upstreams evolve. | This register, the platform cards, the wiki log, and live watch-surface checks now exist. | Deepen drift handling from visibility into automated remediation workflows and richer fixture updates. |

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
- the repo now has a machine-readable platform registry
- the repo now has a maintainer-first in-repo wiki
- the repo now has an explicit identity/crosswalk schema boundary
- the repo now has a typed skill graph for lanes, skills, platforms, and governance constraints
- the repo now has an executable selector plus fixture-backed route tests
- the repo now has a bounded Columbia Basin v0 identity slice
- the repo now has CRITFC, NOAA SPS, and NPAFC source scaffolds
- the repo now has a stock-brief workflow scaffold

Still open at parity-blocking severity:
- identity graph
- behavior tests and golden prompts beyond the selector layer
- governance-aware access beyond `access_tier`
- deterministic composite workflows beyond the stock-brief scaffold
