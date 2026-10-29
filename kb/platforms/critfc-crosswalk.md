# CRITFC Crosswalk Project

- Platform card: [registry/platforms/critfc-crosswalk.json](../../registry/platforms/critfc-crosswalk.json)
- Related skill: [critfc-crosswalk-skill](../../skills/critfc-crosswalk-skill/SKILL.md)

## Current role

CRITFC crosswalk is the Columbia Basin pop/unit reconciliation scaffold for salmon and steelhead naming and boundary context.

## Current posture

- supported: identifier crosswalks
- partial: discovery/search, metadata/schema, entity lookup, hatchery, provenance/versioning, bulk-access ergonomics
- missing: abundance/assessment, telemetry/passage, harvest/fishery, genetics/GSI, package/export

## Why it matters

It is one of the few source-family wrappers that is explicitly about crosswalks rather than just records, but it remains project-specific and legacy-oriented.


## Transport contract

The adapter uses the shared [source transport contract](../../docs/source-transport.md):
explicit HTTPS origins, checked redirects, real final-origin provenance and
typed failures. The synthetic transport tests establish these local behaviors;
they do not establish current service availability.
