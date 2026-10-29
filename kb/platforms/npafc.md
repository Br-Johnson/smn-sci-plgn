# NPAFC

- Platform card: [registry/platforms/npafc.json](../../registry/platforms/npafc.json)
- Related skill: [npafc-skill](../../skills/npafc-skill/SKILL.md)

## Current role

NPAFC is the public catalogue and statistics scaffold for North Pacific salmon-related datasets and time series.

## Current posture

- supported: discovery/search, metadata/schema, provenance/versioning, bulk-access ergonomics
- partial: entity lookup, abundance/assessment, hatchery, harvest/fishery, package/export
- missing: identifier crosswalks, telemetry/passage, genetics/GSI

## Why it matters

It adds a clean public metadata/API lane that is broader and more documented than the legacy web-app sources.


## Transport contract

The adapter uses the shared [source transport contract](../../docs/source-transport.md):
explicit HTTPS origins, checked redirects, real final-origin provenance and
typed failures. The synthetic transport tests establish these local behaviors;
they do not establish current service availability.
