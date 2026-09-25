# Entrypoints (What Is Actually Used?)

Purpose: keep one short, reliable map of what to run, what to edit, and where the canonical gap register lives.

## Run

- Validate the scaffold (structure, registry, graph, thin-front-door contract, evals, watch surfaces): `python3 scripts/validate_scaffold.py`
- Run the selector regression suite: `python3 -m unittest discover -s tests -p 'test_*.py'`
- Validate both plugin manifests with the Claude CLI: `claude plugin validate .`
- Run the behavioural evals (needs model credentials): `claude plugin eval . --allow-tools Bash`
- Run one skill's eval: `claude plugin eval . --case salmon-terms --allow-tools Bash --ablation none --runs 1`
- Install for Claude Code from GitHub: `claude plugin marketplace add Br-Johnson/smn-sci-plgn` then `claude plugin install salmon-science-research@smn-sci-plgn`
- Load for Claude Code during development: `claude --plugin-dir .`
- Install for Codex / OpenAI: `python3 scripts/install_codex_plugin.py`
- Symlink the skills for Claude without the plugin manifest (legacy path): `python3 scripts/install_claude_skills.py`

## Canonical Docs

- Repo overview and setup: `README.md`
- Living parity-gap register: `docs/platform-gap-register.md`
- Thin-front-door contract for adapters: `kb/concepts/thin-front-door.md`
- Machine-readable platform truth: `registry/platforms/`
- Machine-readable routing topology: `registry/skill-graph.json`
- Maintainer-first wiki navigation: `kb/index.md`
- Wiki maintenance rules: `kb/AGENTS.md`

## Canonical Manifests

- Claude Code plugin manifest: `.claude-plugin/plugin.json`
- Claude Code marketplace (this repo lists itself): `.claude-plugin/marketplace.json`
- Codex / OpenAI plugin manifest: `.codex-plugin/plugin.json`
- Both manifests point at the same `skills/` tree and must carry the same `name` and `version`; the validator checks this.

## Canonical Skill Entry Points

- Broad salmon questions: `skills/salmon-research-router-skill/SKILL.md`
- Entity normalization: `skills/salmon-entity-normalizer-skill/SKILL.md`
- Ontology term lookup (smn, gcdfo, external vocabularies via metasalmonpy): `skills/salmon-terms/SKILL.md`
- Salmon Data Package engine (runtime, catalog, ontology fetch, validation): `skills/metasalmon-skill/SKILL.md`
- Crosswalk and harmonization lookups: `skills/critfc-crosswalk-skill/SKILL.md`
- Structured stock briefs: `skills/salmon-stock-brief-workflow-skill/SKILL.md`
- StreamNet access: `skills/streamnet-api-skill/SKILL.md`
- PTAGIS access: `skills/ptagis-skill/SKILL.md`
- RMIS access: `skills/rmis-skill/SKILL.md`
- DART catalog lookups: `skills/dart-query-skill/SKILL.md`
- NOAA population-summary context: `skills/noaa-sps-skill/SKILL.md`
- NPAFC catalogue and statistics: `skills/npafc-skill/SKILL.md`
- Literature lookups: `skills/salmon-literature-skill/SKILL.md`

## Canonical Scripts

- Shared stdlib plumbing for adapters (stdin/stdout, HTTP, raw save): `scripts/_common.py`
- Executable graph selector: `scripts/skill_graph_selector.py`
- Whole-repo structural, contract, eval, and watch-surface validation: `scripts/validate_scaffold.py`
- Term lookup adapter (run with `uv run`): `skills/salmon-terms/scripts/salmon_terms.py`
- Package engine adapter (run with `uv run`): `skills/metasalmon-skill/scripts/metasalmon_api.py`
- Stock-brief contract helper: `skills/salmon-stock-brief-workflow-skill/scripts/stock_brief_contract.py`
- CI validation workflow: `.github/workflows/scaffold-validation.yml`

## Canonical Data Contracts

- Platform card contract (including optional `pinned_releases`): `registry/platform-card.schema.json`
- Identity/crosswalk record contract: `registry/identity-record.schema.json`
- Bounded Columbia Basin slice contract: `registry/identity/columbia-basin-v0.schema.json`
- Skill-graph contract: `registry/skill-graph.schema.json`
- Skill-graph topology: `registry/skill-graph.json`
- Vocabulary for platform and identity status fields: `registry/vocab.json`
- Skill-to-platform mapping (a skill may map to several platforms): `registry/skill-platform-map.json`
- Eval suite (one case per skill): `evals/<skill>/prompt.md` plus `evals/<skill>/graders/*.md`

## What To Edit

- Add or widen a source skill: `skills/<skill-name>/` plus `evals/<skill-name>/`
- Bump a package pin: `registry/platforms/metasalmon.json` `pinned_releases` and the pins in `skills/salmon-terms/scripts/salmon_terms.py` and `skills/metasalmon-skill/scripts/metasalmon_api.py`, in one change
- Release the plugin: bump `version` in both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`, then tag
- Change router topology or typed skill relations: `registry/skill-graph.json`
- Change router graph-selection guidance: `skills/salmon-research-router-skill/references/skill-graph-routing.md`
- Change selector heuristics or fixture expectations: `scripts/skill_graph_selector.py` and `tests/fixtures/skill_graph_selector_cases.json`
- Update the maintained parity and rigor view: `docs/platform-gap-register.md`
- Update source-specific truth: `registry/platforms/<platform>.json`
- Update bounded identity coverage: `registry/identity/columbia-basin-v0.json`
- Update seed identity/crosswalk scaffolding: `registry/identity/seed-crosswalks.json`
- Update narrative platform knowledge: `kb/platforms/` and `kb/concepts/`
- Change user-facing repo scope or setup: `README.md`
