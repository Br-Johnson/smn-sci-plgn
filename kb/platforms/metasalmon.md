# metasalmon

- Platform card: [registry/platforms/metasalmon.json](../../registry/platforms/metasalmon.json)
- Related skill: [metasalmon-skill](../../skills/metasalmon-skill/SKILL.md)

## Current role

`metasalmon` is the current Salmon Data Package engine for package validation, semantic search, and publication helpers.

## Current posture

- supported: discovery/search, metadata/schema, package/export
- partial: entity lookup, identifier-crosswalk support, provenance/versioning, bulk-access ergonomics
- missing: direct assessment, telemetry, harvest, hatchery, and genetics workflows in the current plugin adapter

## Why it matters

This is the strongest current package-first component in the salmon stack, but the plugin only exposes a thin slice of it today.
