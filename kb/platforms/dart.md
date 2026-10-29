# DART

- Platform card: [registry/platforms/dart.json](../../registry/platforms/dart.json)
- Related skill: [dart-query-skill](../../skills/dart-query-skill/SKILL.md)

## Current role

DART is the current scaffold's catalog surface for Columbia River passage, river condition, and hatchery-release query pages.

## Current posture

- supported: discovery/search
- partial: abundance/assessment, telemetry/passage, hatchery, bulk-access ergonomics
- missing: metadata/schema, entity lookup, crosswalks, harvest, genetics, package/export, provenance/versioning

## Why it matters

DART helps the router find the right Columbia query surface, but it is still a page-discovery helper rather than a structured data skill.


## Transport contract

The adapter uses the shared [source transport contract](../../docs/source-transport.md):
explicit HTTPS origins, checked redirects, real final-origin provenance and
typed failures. The synthetic transport tests establish these local behaviors;
they do not establish current service availability.
