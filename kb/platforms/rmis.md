# RMIS

- Platform card: [registry/platforms/rmis.json](../../registry/platforms/rmis.json)
- Related skill: [rmis-skill](../../skills/rmis-skill/SKILL.md)

## Current role

RMIS / RMPC is the current scaffold's coded-wire-tag source.

## Current posture

- partial: discovery/search, metadata/schema, entity lookup, identifier crosswalks, hatchery context, harvest/fishery context, provenance/versioning, bulk-access ergonomics
- missing: abundance/assessment, telemetry, genetics, package/export
- gating remains central: useful data access is authenticated

## Why it matters

RMIS is important for release and recovery context, but the plugin must treat it as an auth-aware workflow rather than a public open-data surface.
