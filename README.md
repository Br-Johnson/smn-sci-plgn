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
- first core skills and script entrypoints
- an authenticated RMIS skill scaffold

What is still intentionally thin:
- cross-jurisdiction identity graph
- full API coverage for salmon portals
- hatchery, genetics, and management-data harmonization
- composite workflows beyond router guidance

## Quick Start

Requirements:
- Python 3.10+
- no third-party Python dependencies

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

## Repo Layout

```text
smn-sci-plgn/
├── .codex-plugin/plugin.json
├── skills/
│   ├── salmon-research-router-skill/
│   ├── salmon-entity-normalizer-skill/
│   ├── streamnet-api-skill/
│   ├── ptagis-skill/
│   ├── rmis-skill/
│   ├── dart-query-skill/
│   └── salmon-literature-skill/
├── scripts/
│   ├── _common.py
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

## Important Upstream Repositories

These repos are foundational to the plugin architecture.

### `salmon-data-mobilization/salmon-domain-ontology`

Role:
- shared cross-organization ontology layer
- long-term canonical source for reusable salmon terms
- right upstream for organization-neutral normalization and interoperability

How it factors in:
- future `smn` ontology lookup skill
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
- future `gcdfo` ontology lookup skill
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
- future `metasalmon` execution skill
- data-package authoring and validation workflows
- term retrieval, semantic QA, and publication helpers

Repo:
- [dfo-pacific-science/metasalmon](https://github.com/dfo-pacific-science/metasalmon)

## Architecture

The intended architecture is:

`router -> normalization layer -> atomic source skills -> future composite workflows -> synthesis`

Near-term workflow:
- use the router for broad questions
- normalize the entities
- call one or more source skills
- synthesize findings with caveats

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

The biggest blockers to full parity with the Life Science Research plugin remain:
- no universal salmon identity graph across `CU`, `SMU`, `DU`, `ESU`, `DPS`, stock, site, hatchery, and tag systems
- inconsistent ontology and measurement semantics across salmon platforms
- many important sources are export- or portal-first rather than API-first
- genetics and telemetry access are partly gated by account or project governance
- hatchery and management semantics remain fragmented
- RMIS is accessible, but mainly through authenticated API or account-gated reporting workflows

## Recommended Next Build Steps

1. Add a first-class salmon identity graph and crosswalk registry.
2. Add ontology-facing skills for `smn` and `gcdfo`.
3. Add a `metasalmon` integration skill instead of re-implementing SDP logic locally.
4. Expand wrappers for `CRITFC`, `NOAA SPS`, `NPAFC`, `NuSEDS`, `PacFIN`, and `FINS`.
5. Add composite workflows for stock briefs, watershed risk briefs, and mixed-stock management briefs.
6. Publish stable sample datasets and golden test prompts.

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
