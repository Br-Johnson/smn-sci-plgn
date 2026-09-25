# metasalmon and metasalmonpy

- Platform card: [registry/platforms/metasalmon.json](../../registry/platforms/metasalmon.json)
- Related skills: [metasalmon-skill](../../skills/metasalmon-skill/SKILL.md), [salmon-terms](../../skills/salmon-terms/SKILL.md)
- Pinned release: `v0.5.0` of [metasalmon](https://github.com/salmon-data-mobilization/metasalmon/releases/tag/v0.5.0) (R) and [metasalmonpy](https://github.com/salmon-data-mobilization/metasalmonpy/releases/tag/v0.5.0) (Python), checked 2026-09-25

## Current role

The two packages are the Salmon Data Package engine: package creation, semantic
term search, validation, review, and publication helpers. metasalmonpy mirrors
metasalmon, and the two keep the same release numbers. Where their behaviour
differs on purpose, metasalmonpy's `PARITY.md` records it.

The plugin calls metasalmonpy for term search (`salmon-terms`) and for package
validation and ontology fetch (`metasalmon-skill`). Each skill documents the R
route as its alternative.

## Current posture

- supported: discovery/search, metadata/schema, package/export
- partial: entity lookup, identifier-crosswalk support, provenance/versioning, bulk-access ergonomics
- missing: direct assessment, telemetry, harvest, hatchery, and genetics workflows in the plugin's adapters

## Why it matters

This is the package-first core of the salmon stack. The plugin is its front
door and holds no logic of its own: a skill calls the packages for anything the
packages can do. Package creation, the review flow, and publication are the
parts not bridged yet.
