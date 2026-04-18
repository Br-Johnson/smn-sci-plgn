# Knowledge Base Maintenance Rules

This `kb/` tree is a maintainer-first wiki for the salmon platform scaffold.

## Layering

There are three layers:

1. Raw sources stay external or immutable.
   Examples: platform docs, ontology repos, package docs, API pages, and repo skills/scripts.
2. `registry/` is the canonical structured truth.
   Platform cards, identity/crosswalk schemas, skill-to-platform mappings, and the typed skill graph live there.
3. `kb/` is the narrative layer.
   Pages here summarize, compare, explain, and cross-link the structured truth.

## Canonical rules

- Do not invent authoritative operational crosswalks.
- Seed identity records may exist for schema validation, but they must be labeled as non-authoritative scaffolding.
- If a fact belongs in structured form, put it in `registry/` first and then summarize it here.
- Treat `registry/skill-graph.json` as the canonical routing topology for skill, lane, platform, and governance relations.
- Platform pages must point to exactly one platform card.
- Gap pages must point to at least one platform page or concept page.
- Update `kb/log.md` whenever a platform card, gap assessment, or wiki structure changes materially.
- Update `kb/index.md` when a new page is added.
- If a skill changes a source surface, update the platform card, the platform page, and the log together.
- If a skill, lane, or pairing relation changes, update the skill graph and the log together.
- If an upstream version or access model changes, update the card, the relevant workflow page, and `docs/platform-gap-register.md` if parity meaning changes.

## Page types

- `platforms/`: one page per source or upstream component
- `concepts/`: architecture and semantic boundary pages
- `gaps/`: recurring cross-platform blockers
- `workflows/`: maintainer playbooks

## Link and evidence policy

- Prefer repo-relative markdown links.
- Link from wiki pages to platform cards, related skills, and upstream docs.
- Keep graph-edge explanations grounded in concrete repo files or upstream URLs.
- Keep citations concrete; do not rely on unlogged chat memory.
