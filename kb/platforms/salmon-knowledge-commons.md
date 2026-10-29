# Salmon knowledge commons

- Platform card: [registry/platforms/salmon-knowledge-commons.json](../../registry/platforms/salmon-knowledge-commons.json)
- Related skill: [commons-card](../../skills/commons-card/SKILL.md)
- Repository: [salmon-data-mobilization/salmon-knowledge-commons](https://github.com/salmon-data-mobilization/salmon-knowledge-commons), private; the skill's pinned commit is `COMMONS_PIN` in its adapter, checked 2026-10-29

## Current role

The commons is the salmon ecosystem's bundle of source-backed concept cards:
what a term means, why a modelling choice went the way it did, and where an
ontology has no term yet. Each card cites its sources, and since the commons
added its ledger tools a card can carry its own citation-ledger table, which
the commons' card-only check reads.

The plugin reaches it through `commons-card`, which runs the commons' own
validator, ledger-table writer and card-only check at a pinned commit against
the user's clone, and prints the commons' contribution rules.

## Current posture

- supported: metadata/schema validation, provenance (in-card citation ledgers)
- partial: bulk-access ergonomics (one adapter over the commons' own scripts)
- partial: local literal research search and exact-card read over an admitted compiler distribution; recorded review state and citations are preserved
- missing: entity lookup, crosswalk resolution, and every observation-data category

## Why it matters

The commons is private and this plugin is public, so the plugin can carry none
of its content and can't fetch it. For contribution checks, the skill copies pinned scripts from the clone's git history and deletes its copies afterwards. The research reader instead
consumes the compiler distribution as data, without executing any of it. When the commons changes those scripts, the adapter
reports the drift and blocks script actions before they run, including ledger
writes. Runtime and checklist remain available for inspection, and moving the
pin is a reviewed plugin change. A bundle-validation pass and a card-ledger
pass report different checks; neither substitutes for the commons' full CI or
independent scientific review.

Research uses the upstream compiler JSON artifacts with explicit local admission,
exact commit and trusted catalog hash. It performs no compilation or acquisition.
[Research usage and limitations](../../skills/commons-card/references/research.md)
distinguish distribution integrity, scientific review and permission to disclose.
