# Entrypoints (What Is Actually Used?)

Purpose: keep one short, reliable map of what to run, what to edit, and where the canonical gap register lives.

## Run

- Validate the scaffold: `python3 scripts/validate_scaffold.py`
- Run the offline regression suite (selector routes, validator guards, adapter startup): `python3 -m unittest discover -s tests -p 'test_*.py'`
- Run the live package-adapter tests, which need uv and network access: `SMN_PLUGIN_LIVE_ADAPTERS=1 python3 -m unittest discover -s tests -p 'test_package_adapters.py'`
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
- Maintainer-first wiki navigation: `kb/index.md`
- Wiki maintenance rules: `kb/AGENTS.md`

## Canonical Skill Entry Points

- Broad salmon questions: `skills/salmon-research-router-skill/SKILL.md`
- Entity normalization: `skills/salmon-entity-normalizer-skill/SKILL.md`
- Crosswalk and harmonization lookups: `skills/critfc-crosswalk-skill/SKILL.md`
- Ontology term search, shared `smn` and DFO `gcdfo` alike: `skills/salmon-terms/SKILL.md`
- Salmon Data Package workflows: `skills/metasalmon-skill/SKILL.md`
- Structured stock briefs: `skills/salmon-stock-brief-workflow-skill/SKILL.md`
- StreamNet access: `skills/streamnet-api-skill/SKILL.md`
- PTAGIS access: `skills/ptagis-skill/SKILL.md`
- RMIS access: `skills/rmis-skill/SKILL.md`
- DART catalog lookups: `skills/dart-query-skill/SKILL.md`
- NOAA population-summary context: `skills/noaa-sps-skill/SKILL.md`
- NPAFC catalogue and statistics: `skills/npafc-skill/SKILL.md`
- Literature lookups: `skills/salmon-literature-skill/SKILL.md`

## Canonical Scripts

- Package adapters, which only marshal JSON to metasalmonpy `v0.5.0`: `skills/salmon-terms/scripts/salmon_terms.py` and `skills/metasalmon-skill/scripts/metasalmon_api.py`
- Plumbing the two adapters share, including the package pin: `scripts/_package_adapter.py`
- Shared stdlib helper utilities: `scripts/_common.py`
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

- Add or widen a source skill: `skills/<skill-name>/`
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
