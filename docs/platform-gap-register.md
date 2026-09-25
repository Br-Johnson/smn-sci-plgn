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
| P0 | Semantics and ontology grounding | Rigor | Term lookup now runs through metasalmonpy, but ontology-backed resolution rules are still thin. There is no authoritative mapping layer from real salmon platform fields to `smn` / `gcdfo` terms. | Lookup alone does not make downstream answers semantically safe. The hard part is consistent field, measure, and unit resolution. | `salmon-terms` calls metasalmonpy `find_terms()` / `sources_for_role()` at the pinned `0.5.0` release (the plugin's own JSON-LD ranker is deleted), and the wiki records the ontology-vs-identity boundary, but automated crosswalk resolution is still absent and lives upstream when it arrives. | Add crosswalk fixtures and package-level semantic QA loops upstream in metasalmonpy; expose them here only as adapters. |
| P1 | Behavioral validation | Rigor | The repo now has selector fixtures, CI, and one `claude plugin eval` case per skill, but not broad answer-quality regression coverage. | Without broader graders and golden prompts, retrieval and synthesis can still drift as upstream APIs and packages change. | `scripts/validate_scaffold.py` validates structure, the thin-front-door contract, eval presence, and watch surfaces; CI runs validation plus selector tests; `evals/<skill>/` gives every skill a smoke case that `claude plugin eval . --allow-tools Bash` runs, but eval runs are not in CI and synthesis-quality regression is still absent. | Widen the eval suite from one smoke case per skill to golden prompts for the router and the stock-brief workflow, and decide whether to run evals in CI with a budget. |
| P0 | Governance-aware access | Platform | Access control is now normalized, but it is still only a thin policy layer. | Gated data sources need explicit policy-aware routing so the agent can distinguish “no data,” “no access,” and “wrong source.” | Platform cards now carry `access_tier`, and the executable selector can block credentialed routes for no-auth requests, but runtime policy remains heuristic and route-specific. | Extend access handling from `access_tier` into richer credential scope, project-gating, and partial-public policy rules. |
| P1 | Source-family breadth | Platform | Coverage is broader, but still not yet near Life Science Research plugin breadth. | Missing wrappers still create structural blind spots in hatchery, harvest, ocean, genetics, and stock-assessment lanes. | Current wrappers now include StreamNet, PTAGIS, RMIS, DART, literature, ontology lookup, `metasalmon`, CRITFC crosswalk, NOAA SPS, and NPAFC. | Add `NuSEDS`, `PacFIN`, and `FINS`, then rank the remaining source-family gaps by join value rather than endpoint count. |
| P1 | Composite workflows | Platform + rigor | The repo now has a stock-brief scaffold, but not durable multi-step workflows with robust reconciliation. | Mature parity requires workflows that convert retrieval into reproducible management or research products. | `salmon-stock-brief-workflow-skill` defines a fixed contract and validation helper, but it is still scaffold-level and not yet a full orchestrated workflow engine. | Extend from stock brief into watershed-risk and mixed-stock management workflows with shared evidence contracts. |
| P1 | Package-first semantic workflows | Platform | The engine is integrated only through thin adapters, by design. | The Salmon Data Package engine is not yet fully exposed to the plugin layer; the adapters cover lookup, fetch, and validation only. | `salmon-terms` and `metasalmon-skill` call metasalmonpy `0.5.0` through `uv` (the R package at `0.5.0` is an interim engine). Exposed today: `sources_for_role()`, `find_terms()`, `fetch_salmon_ontology()`, `validate_salmon_datapackage()`, runtime and catalog inspection. | Add adapters for package creation, reviewed-package reloads, gap detection, and term-request rendering once those upstream surfaces are stable; retire the R engine when the Foundry `salmon` CLI ships. |
| P1 | Provenance and evidence weighting | Rigor | Cross-source conflict handling is mostly narrative. | Parity with deterministic life-science synthesis requires explicit scoring, conflict notes, and reproducible output contracts. | Current source skills return summaries but no shared provenance scorecard. | Define a shared evidence-contract schema and use it in future composite workflows. |
| P2 | Skill-graph routing maturity | Rigor + maintainability | A typed skill graph and executable selector now exist, but lane seeding, subgraph scoring, and availability-aware expansion are still heuristic. | Graph topology now drives real decisions, so parity depends on ranking quality and drift detection when the route behavior changes. | `registry/skill-graph.json` models skill, platform, lane, and governance nodes; `scripts/skill_graph_selector.py` selects routed skill sets; and the selector is fixture-backed. | Extend the selector toward capability-aware ranking, richer auth-state pruning, and golden routing cases tied directly to graph changes. |
| P2 | Change monitoring | Platform + rigor | Skills depend on moving upstream ontologies, package interfaces, and API surfaces. | Without a watchlist, the repo will rot as upstreams evolve. | This register, the platform cards, the wiki log, and live watch-surface checks exist; the validator now compares the metasalmon and metasalmonpy pins with the latest upstream release and warns when a pin is behind. | Deepen drift handling from visibility into automated pin-bump PRs and eval re-runs. |

## Upstream Watchlist

These are the upstream components most likely to force skill updates.

| Component | Current known state | Why it matters | What to watch |
|---|---|---|---|
| `salmon-data-mobilization/salmon-domain-ontology` | Shared ontology, `smn` root advertises version `0.0.3` (modified 2026-08-14). Reached only through metasalmonpy. | Shared semantic layer for cross-organization terms. | Version changes, namespace publication changes, JSON-LD structure, and migration decisions that move terms between namespaces. |
| `dfo-pacific-science/dfo-salmon-ontology` | DFO ontology, published `gcdfo` surface advertises version `0.0.9` (modified 2026-08-16). Reached only through metasalmonpy. | DFO-specific profile layer and boundary decisions against shared `smn`. | Shared-vs-DFO boundary changes, imported shared-term migrations, and published JSON-LD field shape. |
| `salmon-data-mobilization/metasalmon` | Pinned at release `0.5.0` (published 2026-08-26); the `dfo-pacific-science/metasalmon` fork is retired. | Salmon Data Package engine (R); interim engine for `metasalmon-skill`. | New releases versus the pin, exported function signatures, and package-validation behavior. |
| `salmon-data-mobilization/metasalmonpy` | Pinned at release `0.5.0` (published 2026-09-24); not on PyPI, resolved from the git tag through `uv`. | Canonical engine behind `salmon-terms` and `metasalmon-skill`. | New releases versus the pin, `find_terms()` / `sources_for_role()` signatures and source list, validation return shape. |
| RMIS / RMPC API | Public announcement currently says RMIS `5.0`, effective `Apr 2nd, 2026`. | Coded-wire-tag access is important and auth-sensitive. | Auth model, endpoint set, query syntax, and reporting/API divergence. |

## Current Closure State

Recent closures or partial closures:
- ontology lookup is no longer missing as a skill family, and since 2026-09-25 it no longer lives in this repo: `salmon-terms` calls metasalmonpy
- `metasalmon` is no longer only a note in the README; `metasalmon-skill` is Python-first over metasalmonpy `0.5.0` with the R package as an interim engine
- the repo now has a Claude Code plugin manifest and a self-listing marketplace beside the Codex manifest
- the repo now has one `claude plugin eval` case per skill and a validator-enforced thin-front-door contract for adapters
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
- golden prompts and synthesis-quality graders beyond the per-skill smoke evals
- governance-aware access beyond `access_tier`
- deterministic composite workflows beyond the stock-brief scaffold
