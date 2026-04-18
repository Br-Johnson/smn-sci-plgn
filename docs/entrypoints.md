# Entrypoints (What Is Actually Used?)

Purpose: keep one short, reliable map of what to run, what to edit, and where the canonical gap register lives.

## Run

- Validate the scaffold: `python3 scripts/validate_scaffold.py`
- Install for Codex / OpenAI: `python3 scripts/install_codex_plugin.py`
- Install for Claude: `python3 scripts/install_claude_skills.py`

## Canonical Docs

- Repo overview and setup: `README.md`
- Living parity-gap register: `docs/platform-gap-register.md`
- Machine-readable platform truth: `registry/platforms/`
- Machine-readable routing topology: `registry/skill-graph.json`
- Maintainer-first wiki navigation: `kb/index.md`
- Wiki maintenance rules: `kb/AGENTS.md`

## Canonical Skill Entry Points

- Broad salmon questions: `skills/salmon-research-router-skill/SKILL.md`
- Entity normalization: `skills/salmon-entity-normalizer-skill/SKILL.md`
- Shared ontology lookup: `skills/smn-ontology-skill/SKILL.md`
- DFO ontology lookup: `skills/gcdfo-ontology-skill/SKILL.md`
- Salmon Data Package workflows: `skills/metasalmon-skill/SKILL.md`
- StreamNet access: `skills/streamnet-api-skill/SKILL.md`
- PTAGIS access: `skills/ptagis-skill/SKILL.md`
- RMIS access: `skills/rmis-skill/SKILL.md`
- DART catalog lookups: `skills/dart-query-skill/SKILL.md`
- Literature lookups: `skills/salmon-literature-skill/SKILL.md`

## Canonical Scripts

- Shared JSON-LD ontology lookup helper: `scripts/ontology_lookup_common.py`
- Shared stdlib helper utilities: `scripts/_common.py`
- Whole-repo structural and watch-surface validation: `scripts/validate_scaffold.py`

## Canonical Data Contracts

- Platform card contract: `registry/platform-card.schema.json`
- Identity/crosswalk record contract: `registry/identity-record.schema.json`
- Skill-graph contract: `registry/skill-graph.schema.json`
- Skill-graph topology: `registry/skill-graph.json`
- Vocabulary for platform and identity status fields: `registry/vocab.json`
- Skill-to-platform mapping: `registry/skill-platform-map.json`

## What To Edit

- Add or widen a source skill: `skills/<skill-name>/`
- Change router topology or typed skill relations: `registry/skill-graph.json`
- Change router graph-selection guidance: `skills/salmon-research-router-skill/references/skill-graph-routing.md`
- Update the maintained parity and rigor view: `docs/platform-gap-register.md`
- Update source-specific truth: `registry/platforms/<platform>.json`
- Update seed identity/crosswalk scaffolding: `registry/identity/seed-crosswalks.json`
- Update narrative platform knowledge: `kb/platforms/` and `kb/concepts/`
- Change user-facing repo scope or setup: `README.md`
