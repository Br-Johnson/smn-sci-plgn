# Salmon Science Research

Open-source salmon ecology, conservation, and management-science workflows for agentic tools.

Canonical repository:

- [Br-Johnson/smn-sci-plgn](https://github.com/Br-Johnson/smn-sci-plgn)

This repository is a thin skills front door. It works in two clients from one
`skills/` tree:

- Claude Code plugin mode via [.claude-plugin/plugin.json](./.claude-plugin/plugin.json), with a self-listing marketplace in [.claude-plugin/marketplace.json](./.claude-plugin/marketplace.json)
- Codex / OpenAI plugin mode via [.codex-plugin/plugin.json](./.codex-plugin/plugin.json)

The design follows the same high-level pattern as the Life Science Research plugin:

- a router for broad requests
- a normalization layer for salmon entities
- source-specific atomic skills
- compact synthesis instead of raw dumps by default

with one rule on top, taken from the Salmon Science Foundry plan: **a skill
calls a pinned, released package, CLI, or public API and holds no logic of its
own.** The packages do the work; this repository routes to them. The contract
and its static check are described in
[kb/concepts/thin-front-door.md](./kb/concepts/thin-front-door.md).

## Status

This is a `0.1.0` scaffold, not a complete salmon platform.

What is real now:
- Claude Code and Codex plugin manifests over one `skills/` tree, plus a marketplace entry so the repo installs from GitHub
- MIT license
- `salmon-terms`: ontology term lookup (shared `smn`, DFO `gcdfo`, and the external vocabularies metasalmonpy searches) through metasalmonpy `find_terms()` / `sources_for_role()`, pinned at `v0.5.0` and run with `uv`
- `metasalmon-skill`: Salmon Data Package engine actions (runtime, catalog, ontology fetch, validation) through metasalmonpy by default, with the `metasalmon` R package as an interim engine
- an authenticated RMIS skill scaffold and narrow StreamNet, PTAGIS, DART, NPAFC, NOAA SPS, CRITFC, and PubMed adapters
- one `claude plugin eval` case per skill under `evals/`
- a validator that enforces manifest agreement, the thin-front-door adapter contract, eval presence, registry and graph consistency, and upstream release pins
- CI workflow and selector regression tests
- a living parity-gap register in `docs/platform-gap-register.md`
- a machine-readable platform registry in `registry/` and a typed skill graph in `registry/skill-graph.json`
- a bounded Columbia Basin v0 identity slice with non-authoritative identity hints
- a scaffolded stock-brief composite workflow
- a maintainer-first in-repo knowledge base in `kb/`

What is still intentionally thin:
- authoritative cross-jurisdiction identity graph coverage
- full API coverage for salmon portals
- hatchery, genetics, and management-data harmonization
- composite workflows beyond the stock-brief scaffold
- golden prompts and synthesis-quality graders beyond the per-skill smoke evals
- package creation, term-request rendering, and publication bridges (they stay upstream until those surfaces are stable)

## Quick Start

Requirements:
- Python 3.10+ (adapter scripts use the stdlib only)
- [`uv`](https://docs.astral.sh/uv/) for `salmon-terms` and `metasalmon-skill`; the scripts declare their pinned metasalmonpy dependency inline and `uv run` resolves it
- network access on first run so `uv` can build the cached environment from the pinned git tag (metasalmonpy is not on PyPI)
- optional: `Rscript` plus `metasalmon` `0.5.0` installed in R, for the interim R engine of `metasalmon-skill`
- optional: API keys for StreamNet, PTAGIS, and RMIS

Install for Claude Code from GitHub:

```bash
claude plugin marketplace add Br-Johnson/smn-sci-plgn
claude plugin install salmon-science-research@smn-sci-plgn
```

Load for Claude Code while developing, without a marketplace:

```bash
claude --plugin-dir .
```

Install for Codex / OpenAI:

```bash
python3 scripts/install_codex_plugin.py
```

This script:
- symlinks the repo into `~/plugins/salmon-science-research`
- adds or updates an entry in `~/.agents/plugins/marketplace.json`

Legacy path for Claude without the plugin manifest (symlinks each skill into `~/.claude/skills/`):

```bash
python3 scripts/install_claude_skills.py
```

Validate the scaffold, the manifests, and the adapter contract:

```bash
python3 scripts/validate_scaffold.py
claude plugin validate .
```

Run the selector regression tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the behavioural evals (each case spawns model runs against your credentials):

```bash
claude plugin eval . --allow-tools Bash
claude plugin eval . --case salmon-terms --allow-tools Bash --ablation none --runs 1
```

Try the two package adapters directly:

```bash
echo '{"action":"find_terms","query":"escapement","role":"variable","sources":["smn"],"max_items":3}' | uv run skills/salmon-terms/scripts/salmon_terms.py
echo '{"action":"runtime"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py
```

## Repo Layout

```text
smn-sci-plgn/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .codex-plugin/plugin.json
├── docs/
│   ├── entrypoints.md
│   └── platform-gap-register.md
├── evals/
│   └── <skill>/prompt.md + graders/*.md
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
│   ├── salmon-terms/
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

## Skills

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

### `salmon-terms`

Thin adapter over metasalmonpy `find_terms()` and `sources_for_role()`, run
with `uv` at the pinned `v0.5.0` release.

Current coverage:
- role-aware term search across `smn`, `gcdfo`, and the external vocabularies metasalmonpy knows (`ols`, `nvs`, `zooma`, `bioportal`, `qudt`, `gbif`, `worms`)
- explicit source allowlists (`["smn"]` for shared-only, `["smn","gcdfo"]` for the two salmon ontologies)
- default source order per semantic role
- per-source diagnostics, so "no hit" and "source did not answer" stay distinct

This replaces the repo's former `smn-ontology-skill`, `gcdfo-ontology-skill`,
and JSON-LD ranker; the ranking now lives upstream.

### `metasalmon-skill`

Thin adapter over the Salmon Data Package engine. Python-first: metasalmonpy
`v0.5.0` through `uv`; the `metasalmon` R package `0.5.0` is an interim engine
selected with `{"engine":"r"}` until the Foundry `salmon` CLI ships.

Current coverage:
- runtime and pin check (`pin_matches`)
- action catalog and package exports
- `fetch_salmon_ontology()`
- `validate_salmon_datapackage()` with the engine's typed issue rows on failure

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

These repos are foundational to the plugin architecture. Skills call them;
they do not re-implement them.

### `salmon-data-mobilization/salmon-domain-ontology`

Role:
- shared cross-organization ontology layer
- long-term canonical source for reusable salmon terms
- right upstream for organization-neutral normalization and interoperability

How it factors in:
- reached through `salmon-terms` (metasalmonpy `smn` source)
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
- reached through `salmon-terms` (metasalmonpy `gcdfo` source)
- DFO-aware normalization
- shared-vs-DFO term-boundary decisions

Repo:
- [dfo-pacific-science/dfo-salmon-ontology](https://github.com/dfo-pacific-science/dfo-salmon-ontology)

### `salmon-data-mobilization/metasalmon` and `salmon-data-mobilization/metasalmonpy`

Role:
- the Salmon Data Package engine: package creation, semantic suggestion and review, term retrieval, ontology fetch, validation, and publication helpers
- metasalmonpy mirrors the R package's API in Python and is the canonical engine for this plugin
- something this plugin integrates with rather than replaces

How it factors in:
- `salmon-terms` and `metasalmon-skill` are adapters over the pinned `0.5.0` releases
- data-package validation workflows
- term retrieval and semantic QA

Repos:
- [salmon-data-mobilization/metasalmon](https://github.com/salmon-data-mobilization/metasalmon) (R, release `v0.5.0`)
- [salmon-data-mobilization/metasalmonpy](https://github.com/salmon-data-mobilization/metasalmonpy) (Python, release `v0.5.0`, installed from the git tag)

The former `dfo-pacific-science/metasalmon` fork is retired and no longer referenced here.

## Architecture

The intended architecture is:

`router -> semantic or lexical seed -> normalization layer -> skill-graph expansion -> atomic adapters over pinned packages and APIs -> future composite workflows -> synthesis`

The supporting data split is:

`ontologies as schema -> registry/identity as crosswalk data -> registry/platforms as source truth (with release pins) -> registry/skill-graph as routing topology -> kb/ as narrative maintenance layer`

Near-term workflow:
- use the router for broad questions
- seed 1 to 3 candidate lanes
- normalize the entities
- expand through the skill graph
- prune or explain routes using platform `access_tier`
- call one or more adapters
- optionally wrap the evidence in a stock-brief contract
- synthesize findings with caveats

Canonical repo-maintenance docs:
- [docs/entrypoints.md](./docs/entrypoints.md)
- [docs/platform-gap-register.md](./docs/platform-gap-register.md)
- [kb/concepts/thin-front-door.md](./kb/concepts/thin-front-door.md)
- [kb/index.md](./kb/index.md)

## Open-Source Strategy

This scaffold is intentionally vendor-light:

- skills are plain `SKILL.md` directories with local adapter scripts
- adapter scripts use the Python stdlib plus, where a package is called, a pinned release resolved by `uv` from inline script metadata
- no private MCP servers are required
- no vendor-specific app connectors are required
- no `bin/` shim, so the same tree installs on claude.ai and in Claude Code

That makes the repo portable:
- Claude Code installs it as a plugin from the marketplace entry
- Codex/OpenAI can consume it as a plugin bundle
- either client reads the same `skills/` directories

That also keeps responsibilities clean:
- ontologies stay authoritative in the ontology repos
- retrieval, ranking, and package logic stay authoritative in `metasalmon` / `metasalmonpy`
- this plugin is the orchestration and synthesis layer over those assets, and the validator refuses adapters that start growing logic

## Known Platform Gaps

This repo does not solve the deeper salmon-platform problems yet.

The maintained register now lives here:
- [docs/platform-gap-register.md](./docs/platform-gap-register.md)

Per-platform truth now lives here:
- [registry/platforms/](./registry/platforms/)
- [kb/platforms/](./kb/platforms/)

The highest-current blockers remain:
- no authoritative salmon identity graph across `CU`, `SMU`, `DU`, `ESU`, `DPS`, stock, site, hatchery, and tag systems
- term lookup now runs upstream, but ontology-backed crosswalk resolution is still thin
- many important sources are export- or portal-first rather than API-first
- genetics and telemetry access are partly gated by account or project governance
- hatchery and management semantics remain fragmented
- evals are one smoke case per skill, not golden coverage

## Recommended Next Build Steps

1. Turn the seed identity layer into authoritative cross-system coverage.
2. Extend the selector from heuristic lane scoring into capability-aware subgraph ranking and richer auth-state pruning.
3. Widen the eval suite from smoke cases to golden prompts for the router and the stock-brief workflow.
4. Expand wrappers for `NuSEDS`, `PacFIN`, and `FINS`.
5. Add adapters for package creation and post-review publication flows once the upstream surfaces are stable.
6. Retire the interim R engine when the Foundry `salmon` CLI ships.
7. Add watershed-risk and mixed-stock management workflows alongside the stock-brief scaffold.
8. Turn access tiers into a fuller policy layer for credentials, project gating, and partial-public surfaces.

## Sources Used For This Scaffold

- Router-plus-skill-family pattern adapted from the Life Science Research plugin design
- [Claude Code plugin docs](https://code.claude.com/docs/en/plugins), [manifest reference](https://code.claude.com/docs/en/plugins-reference), [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference), and [plugin evals](https://code.claude.com/docs/en/plugin-evals)
- [StreamNet REST API docs](https://www.streamnet.org/resources/exchange-tools/rest-api-documentation/)
- [PTAGIS API docs](https://www.ptagis.org/Content/DataSpecification/topics/api.htm)
- [RMPC API page](https://www.rmpc.org/submission/api/)
- [RMIS API docs repo](https://github.com/PSMFC-Streamnet-RMPC/api-docs)
- [RMIS announcement page](https://www.rmis.org/include/rmis_announce.html)
- [DART overview](https://www.cbr.washington.edu/dart/overview)
- [NCBI E-utilities docs](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [salmon-data-mobilization/salmon-domain-ontology](https://github.com/salmon-data-mobilization/salmon-domain-ontology)
- [dfo-pacific-science/dfo-salmon-ontology](https://github.com/dfo-pacific-science/dfo-salmon-ontology)
- [salmon-data-mobilization/metasalmon](https://github.com/salmon-data-mobilization/metasalmon)
- [salmon-data-mobilization/metasalmonpy](https://github.com/salmon-data-mobilization/metasalmonpy)
