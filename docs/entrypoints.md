# Entrypoints (What Is Actually Used?)

Purpose: keep one short, reliable map of what to run, what to edit, and where the canonical gap register lives.

## Run

- Validate the scaffold: `python3 scripts/validate_scaffold.py`
- Run the offline regression suite (selector routes, validator guards, adapter startup): `python3 -m unittest discover -s tests -p 'test_*.py'`
- Run the live package-adapter tests, which need uv and network access: `SMN_PLUGIN_LIVE_ADAPTERS=1 python3 -m unittest discover -s tests -p 'test_package_adapters.py'`
- Run one eval case against a live model: `claude plugin eval . --no-publish --ablation none --runs 1 --case <case> --allow-tools Bash`, plus `Write` for the stock-brief case and one `"WebFetch(domain:<host>)"` grant for each host the case's `description` names. It needs Claude Code 2.1.269 or later, and every run is billed model usage. `scripts/validate_scaffold.py` checks the case files offline, and no case has been scored yet.
- Install for Codex / OpenAI: `python3 scripts/install_codex_plugin.py`
- Install for Claude Code as a plugin: `claude plugin marketplace add Br-Johnson/smn-sci-plgn`, then `claude plugin install salmon-science-research@smn-sci-plgn`
- Link the skills into `~/.claude/skills/` for local development: `python3 scripts/install_claude_skills.py`
- Official Claude Code checks, when the `claude` CLI is installed: `claude plugin validate --strict .` for the marketplace, and `claude plugin validate --strict .claude-plugin/plugin.json` for the plugin and its skills. Run both, because at the repository root the CLI reads only the marketplace.

## Canonical Docs

- Repo overview and setup: `README.md`
- Plugin manifests, which must agree: `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Living parity-gap register: `docs/platform-gap-register.md`
- Machine-readable platform truth: `registry/platforms/`
- Machine-readable routing topology: `registry/skill-graph.json`
- Behavioural eval cases, one or more per skill: `evals/<case>/prompt.md` and `evals/<case>/graders/`
- Maintainer-first wiki navigation: `kb/index.md`
- Wiki maintenance rules: `kb/AGENTS.md`

## Canonical Skill Entry Points

- Broad salmon questions: `skills/salmon-research-router-skill/SKILL.md`
- Entity normalization: `skills/salmon-entity-normalizer-skill/SKILL.md`
- Crosswalk and harmonization lookups: `skills/critfc-crosswalk-skill/SKILL.md`
- Ontology term search, shared `smn` and DFO `gcdfo` alike: `skills/salmon-terms/SKILL.md`
- Controlled-vocabulary authoring and W3ID/GitHub Pages publication preparation: `skills/controlled-vocabulary/SKILL.md`
- Salmon Data Package workflows: `skills/metasalmon-skill/SKILL.md`
- Judging a package's semantic review packet: `skills/sdp-semantic-review/SKILL.md`
- Writing and checking salmon knowledge commons cards: `skills/commons-card/SKILL.md`
- Structured stock briefs: `skills/salmon-stock-brief-workflow-skill/SKILL.md`
- StreamNet access: `skills/streamnet-api-skill/SKILL.md`
- PTAGIS access: `skills/ptagis-skill/SKILL.md`
- RMIS access: `skills/rmis-skill/SKILL.md`
- DART catalog lookups: `skills/dart-query-skill/SKILL.md`
- NOAA population-summary context: `skills/noaa-sps-skill/SKILL.md`
- NPAFC catalogue and statistics: `skills/npafc-skill/SKILL.md`
- Literature lookups: `skills/salmon-literature-skill/SKILL.md`

## Canonical Scripts

- Package adapters, which only marshal JSON to metasalmonpy `v0.6.0`: `skills/salmon-terms/scripts/salmon_terms.py` and `skills/metasalmon-skill/scripts/metasalmon_api.py`
- Plumbing the two adapters share, including the package pin: `scripts/_package_adapter.py`
- Commons adapter, which runs the commons' own scripts at its pinned commit against the user's clone: `skills/commons-card/scripts/commons_card.py`
  - `runtime`/`checklist` inspect the pin and drift; script actions return `upstream_drift` before running when tools, schema or contribution rules differ.
  - Offline contract checks: `python3 -m unittest discover -s tests -p 'test_commons_card.py'`. With an authorized clone, set `SALMON_COMMONS_DIR` to enable the real-tool synthetic controls and read-only bundle/ledger checks.
- Local CV authoring helper, copied into each new project and requiring only Python's standard library: `skills/controlled-vocabulary/scripts/controlled_vocabulary.py`. Run `init`, `validate`, `release`, `build`, or `prepare-publication`; publication preparation performs no external action. Regression seam: `tests/test_controlled_vocabulary.py`.
- Shared HTTP reads, typed source failures, retrieval ledger and credential-safe output/file handling: `scripts/_common.py`; contract: `docs/source-transport.md`; regressions: `tests/test_public_source_transport.py`
- Authenticated-source origin, redirect and redaction policy: `scripts/_source_auth.py`; user-run setup: `docs/source-authentication.md`; regressions: `tests/test_source_credentials.py`
- Executable graph selector: `scripts/skill_graph_selector.py`
- Whole-repo structural and watch-surface validation: `scripts/validate_scaffold.py`
- Stock-brief contract helper: `skills/salmon-stock-brief-workflow-skill/scripts/stock_brief_contract.py`
- CI validation workflow: `.github/workflows/scaffold-validation.yml`

## Canonical Data Contracts

- Platform card contract: `registry/platform-card.schema.json`
- Identity/crosswalk record contract: `registry/identity-record.schema.json`
- Bounded Columbia Basin slice contract: `registry/identity/columbia-basin-v0.schema.json`
- Skill-graph contract: `registry/skill-graph.schema.json`
- Skill-graph topology: `registry/skill-graph.json`
- Vocabulary for platform and identity status fields: `registry/vocab.json`
- Skill-to-platform mapping: `registry/skill-platform-map.json`

## What To Edit

- Add or widen a source skill: `skills/<skill-name>/`, plus its eval case under `evals/<skill-name>/`, which validation requires
- Change router topology or typed skill relations: `registry/skill-graph.json`
- Change router graph-selection guidance: `skills/salmon-research-router-skill/references/skill-graph-routing.md`
- Change selector heuristics or fixture expectations: `scripts/skill_graph_selector.py` and `tests/fixtures/skill_graph_selector_cases.json`
- Update the maintained parity and rigor view: `docs/platform-gap-register.md`
- Update source-specific truth: `registry/platforms/<platform>.json`
- Update bounded identity coverage: `registry/identity/columbia-basin-v0.json`
- Update seed identity/crosswalk scaffolding: `registry/identity/seed-crosswalks.json`
- Update narrative platform knowledge: `kb/platforms/` and `kb/concepts/`
- Change user-facing repo scope or setup: `README.md`
- Change plugin metadata: `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` together, since validation fails until they agree
- Move the metasalmon or metasalmonpy pin: every copy in one change, meaning `scripts/_package_adapter.py`, the inline metadata block of both adapter scripts, and the docs that name the tag. Validation fails until they agree.

## Private research project path

- Workbench export inspection and selected contribution preview: `skills/salmon-workbench-skill/SKILL.md`.
- Framework template/check: `skills/salmon-research-framework-skill/SKILL.md`.
- One shared implementation: `scripts/workbench_project.py`; each skill has a portable wrapper.
- Contract/semantic/privacy regressions: `tests/test_workbench_project.py`.
- No hosted client, model fitting, graph publication or human decision application is implemented in this path.
