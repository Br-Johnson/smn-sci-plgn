# Salmon Science Research

Open-source salmon ecology, conservation, and management-science workflows for agentic tools.

Canonical repository:

- [Br-Johnson/smn-sci-plgn](https://github.com/Br-Johnson/smn-sci-plgn)

This repository is scaffolded to work in two modes:

- Codex / OpenAI plugin mode via [.codex-plugin/plugin.json](./.codex-plugin/plugin.json)
- Claude skill-bundle mode via [skills/](./skills/)

The design follows the same high-level pattern as the Life Science Research plugin:

- a router for broad requests
- a normalization layer for salmon entities
- source-specific atomic skills
- compact synthesis instead of raw dumps by default

## Status

This is a scaffolded `0.0.1` repo, not a complete salmon platform.

What is real now:
- plugin manifest
- MIT license
- Claude and Codex install scripts
- validation script
- CI workflow and selector regression tests
- first core skills and script entrypoints
- an authenticated RMIS skill scaffold
- shared and DFO ontology lookup skills
- a thin `metasalmon` execution skill
- a living parity-gap register in `docs/platform-gap-register.md`
- a machine-readable platform registry in `registry/`
- a typed router-adjacent skill graph in `registry/skill-graph.json`
- an executable graph selector with fixture-backed routing cases
- a bounded Columbia Basin v0 identity slice with non-authoritative identity hints
- a seed identity/crosswalk data layer with explicit schemas
- three new source scaffolds: `CRITFC`, `NOAA SPS`, and `NPAFC`
- a scaffolded stock-brief composite workflow
- a maintainer-first in-repo knowledge base in `kb/`

What is still intentionally thin:
- authoritative cross-jurisdiction identity graph coverage
- full API coverage for salmon portals
- hatchery, genetics, and management-data harmonization
- composite workflows beyond the stock-brief scaffold
- golden prompts and broader behavior fixtures beyond the selector layer

## Quick Start

Requirements:
- Python 3.10+
- no third-party Python dependencies
- optional: `Rscript` plus installed `metasalmon` for `metasalmon-skill`

Install for Codex / OpenAI:

```bash
python3 scripts/install_codex_plugin.py
```

This script:
- symlinks the repo into `~/plugins/salmon-science-research`
- adds or updates an entry in `~/.agents/plugins/marketplace.json`

Install the skills for Claude:

```bash
python3 scripts/install_claude_skills.py
```

This script symlinks each directory under `skills/` into `~/.claude/skills/`.

Validate the scaffold:

```bash
python3 scripts/validate_scaffold.py
```

Run the selector regression tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Repo Layout

```text
smn-sci-plgn/
├── .codex-plugin/plugin.json
├── docs/
│   ├── entrypoints.md
│   └── platform-gap-register.md
├── registry/
│   ├── skill-graph.json
│   ├── skill-graph.schema.json
│   ├── platforms/
│   └── identity/
├── tests/
│   └── fixtures/
├── kb/
│   ├── AGENTS.md
│   ├── platforms/
│   ├── concepts/
│   ├── gaps/
│   └── workflows/
├── skills/
│   ├── salmon-research-router-skill/
│   ├── salmon-entity-normalizer-skill/
│   ├── smn-ontology-skill/
│   ├── gcdfo-ontology-skill/
│   ├── metasalmon-skill/
│   ├── streamnet-api-skill/
│   ├── ptagis-skill/
│   ├── rmis-skill/
│   ├── dart-query-skill/
│   ├── salmon-literature-skill/
│   ├── critfc-crosswalk-skill/
│   ├── noaa-sps-skill/
│   ├── npafc-skill/
│   └── salmon-stock-brief-workflow-skill/
├── .github/
│   └── workflows/
├── scripts/
│   ├── _common.py
│   ├── skill_graph_selector.py
│   ├── install_codex_plugin.py
│   ├── install_claude_skills.py
│   └── validate_scaffold.py
└── LICENSE
```

## Initial Skills

### `salmon-research-router-skill`

Default entrypoint for broad salmon questions.

Use it to:
- classify a user request into salmon-science lanes
- normalize entities first
- choose the smallest useful skill set
- decide when subagents are worth the coordination cost

### `salmon-entity-normalizer-skill`

Seed normalization layer for:
- species and salmonid aliases
- jurisdiction names
- management-unit systems such as `CU`, `SMU`, `DU`, `ESU`, `DPS`
- common identifier tokens such as `HUC`, `PIT`, and `CWT`

### `smn-ontology-skill`

Lookup skill for the shared Salmon Domain Ontology.

Current coverage:
- ontology metadata and version lookup
- label / definition / IRI search over published `smn.jsonld`
- exact term fetch by local name, prefixed id, or full IRI

### `gcdfo-ontology-skill`

Lookup skill for the DFO-specific Salmon Ontology.

Current coverage:
- ontology metadata and version lookup
- label / definition / IRI search over published `gcdfo.jsonld`
- exact term fetch by local name, prefixed id, or full IRI

### `metasalmon-skill`

Thin execution wrapper around the installed `metasalmon` R package.

Current coverage:
- runtime and package-version inspection
- function catalog for current supported workflows
- `sources_for_role()`
- `find_terms()`
- `fetch_salmon_ontology()`
- `validate_salmon_datapackage()`

### `streamnet-api-skill`

Narrow wrapper around the documented StreamNet REST surface.

Current coverage:
- coordinated assessment table listing
- coordinated assessment table schema fetch
- coordinated assessment record fetch
- generic GET request path

### `ptagis-skill`

Narrow wrapper around documented PTAGIS endpoints.

Current coverage:
- interrogation-site observations
- site-code listings
- file listings
- validation-code metadata
- report listing and download paths

### `rmis-skill`

Authenticated wrapper for the live RMIS / RMPC API plus public RMIS status lookups.

Current coverage:
- public RMIS version announcement lookup
- API login for API key or JWT retrieval
- authenticated `release`, `recovery`, `location`, `catchsample`, `description`, and `files` GET calls
- generic request path for future expansion

### `dart-query-skill`

Catalog and fetch helper for important Columbia River DART query surfaces.

Current coverage:
- built-in query catalog
- page lookup by short name or path

### `salmon-literature-skill`

Functional PubMed-backed literature search for salmon topics using NCBI E-utilities.

Current coverage:
- query search
- compact article summaries
- optional raw JSON persistence

### `critfc-crosswalk-skill`

CRITFC crosswalk and ArcGIS REST helper for Columbia Basin pop or unit reconciliation.

Current coverage:
- project-page fetch
- REST-root fetch
- bounded public request path

### `noaa-sps-skill`

Legacy NOAA Salmon Population Summary page and help-doc wrapper.

Current coverage:
- home page fetch
- help page fetch
- bounded public request path

### `npafc-skill`

Public NPAFC CKAN catalogue and statistics wrapper.

Current coverage:
- dataset search
- dataset show
- resource show
- statistics page fetch
- bounded public request path

### `salmon-stock-brief-workflow-skill`

Structured workflow scaffold for provenance-aware salmon stock briefs.

Current coverage:
- fixed markdown contract
- template generation
- contract validation helper

## Important Upstream Repositories

These repos are foundational to the plugin architecture.

### `salmon-data-mobilization/salmon-domain-ontology`

Role:
- shared cross-organization ontology layer
- long-term canonical source for reusable salmon terms
- right upstream for organization-neutral normalization and interoperability

How it factors in:
- current `smn-ontology-skill`
- shared semantic normalization
- cross-organization entity alignment

Repo:
- [salmon-data-mobilization/salmon-domain-ontology](https://github.com/salmon-data-mobilization/salmon-domain-ontology)

### `dfo-pacific-science/dfo-salmon-ontology`

Role:
- DFO-specific ontology and operational profile layer
- right upstream for DFO-only concepts, program semantics, and stewardship workflows
- already wired to import the shared `smn` layer

How it factors in:
- current `gcdfo-ontology-skill`
- DFO-aware normalization
- shared-vs-DFO term-boundary decisions

Repo:
- [dfo-pacific-science/dfo-salmon-ontology](https://github.com/dfo-pacific-science/dfo-salmon-ontology)

### `dfo-pacific-science/metasalmon`

Role:
- operational Salmon Data Package engine
- strongest current implementation of package creation, semantic suggestion, ontology retrieval, and validation
- something this plugin should integrate with rather than replace

How it factors in:
- current `metasalmon-skill` as a thin execution adapter
- data-package authoring and validation workflows
- term retrieval, semantic QA, and publication helpers

Repo:
- [dfo-pacific-science/metasalmon](https://github.com/dfo-pacific-science/metasalmon)

## Architecture

The intended architecture is:

`router -> semantic or lexical seed -> normalization layer -> skill-graph expansion -> atomic source skills -> future composite workflows -> synthesis`

The supporting data split is now:

`ontologies as schema -> registry/identity as crosswalk data -> registry/platforms as source truth -> registry/skill-graph as routing topology -> kb/ as narrative maintenance layer`

Near-term workflow:
- use the router for broad questions
- seed 1 to 3 candidate lanes
- normalize the entities
- expand through the skill graph
- prune or explain routes using platform `access_tier`
- call one or more source skills
- optionally wrap the evidence in a stock-brief contract
- synthesize findings with caveats

Canonical repo-maintenance docs:
- [docs/entrypoints.md](./docs/entrypoints.md)
- [docs/platform-gap-register.md](./docs/platform-gap-register.md)
- [kb/index.md](./kb/index.md)

## Open-Source Strategy

This scaffold is intentionally vendor-light:

- skills are plain `SKILL.md` directories with local scripts
- scripts use Python stdlib only
- no private MCP servers are required
- no vendor-specific app connectors are required

That makes the repo portable:
- Codex/OpenAI can consume it as a plugin bundle
- Claude can consume the same skill directories directly

That also keeps responsibilities clean:
- ontologies stay authoritative in the ontology repos
- data-package logic stays authoritative in `metasalmon`
- this plugin becomes the orchestration and synthesis layer over those assets

## Known Platform Gaps

This repo does not solve the deeper salmon-platform problems yet.

The maintained register now lives here:
- [docs/platform-gap-register.md](./docs/platform-gap-register.md)

Per-platform truth now lives here:
- [registry/platforms/](./registry/platforms/)
- [kb/platforms/](./kb/platforms/)

The highest-current blockers remain:
- no authoritative salmon identity graph across `CU`, `SMU`, `DU`, `ESU`, `DPS`, stock, site, hatchery, and tag systems
- ontology lookup now exists, but ontology-backed crosswalk resolution is still thin
- many important sources are export- or portal-first rather than API-first
- genetics and telemetry access are partly gated by account or project governance
- hatchery and management semantics remain fragmented
- there are still no broad golden answer fixtures across the full skill suite

## Recommended Next Build Steps

1. Turn the seed identity layer into authoritative cross-system coverage.
2. Extend the selector from heuristic lane scoring into capability-aware subgraph ranking and richer auth-state pruning.
3. Add golden prompts and per-skill smoke fixtures beyond the selector suite.
4. Expand wrappers for `NuSEDS`, `PacFIN`, and `FINS`.
5. Deepen `metasalmon` coverage to package creation and post-review publication flows.
6. Add watershed-risk and mixed-stock management workflows alongside the stock-brief scaffold.
7. Turn access tiers into a fuller policy layer for credentials, project gating, and partial-public surfaces.

## Sources Used For This Scaffold

- Router-plus-skill-family pattern adapted from the Life Science Research plugin design
- [StreamNet REST API docs](https://www.streamnet.org/resources/exchange-tools/rest-api-documentation/)
- [PTAGIS API docs](https://www.ptagis.org/Content/DataSpecification/topics/api.htm)
- [RMPC API page](https://www.rmpc.org/submission/api/)
- [RMIS API docs repo](https://github.com/PSMFC-Streamnet-RMPC/api-docs)
- [RMIS announcement page](https://www.rmis.org/include/rmis_announce.html)
- [DART overview](https://www.cbr.washington.edu/dart/overview)
- [NCBI E-utilities docs](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [salmon-data-mobilization/salmon-domain-ontology](https://github.com/salmon-data-mobilization/salmon-domain-ontology)
- [dfo-pacific-science/dfo-salmon-ontology](https://github.com/dfo-pacific-science/dfo-salmon-ontology)
- [dfo-pacific-science/metasalmon](https://github.com/dfo-pacific-science/metasalmon)
