# Entrypoints (What Is Actually Used?)

Purpose: keep one short, reliable map of what to run, what to edit, and where the canonical gap register lives.

## Run

- Validate the scaffold: `python3 scripts/validate_scaffold.py`
- Install for Codex / OpenAI: `python3 scripts/install_codex_plugin.py`
- Install for Claude: `python3 scripts/install_claude_skills.py`

## Canonical Docs

- Repo overview and setup: `README.md`
- Living parity-gap register: `docs/platform-gap-register.md`

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

## What To Edit

- Add or widen a source skill: `skills/<skill-name>/`
- Update the maintained parity and rigor view: `docs/platform-gap-register.md`
- Change user-facing repo scope or setup: `README.md`
