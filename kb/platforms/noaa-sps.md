# NOAA SPS

- Platform card: [registry/platforms/noaa-sps.json](../../registry/platforms/noaa-sps.json)
- Related skill: [noaa-sps-skill](../../skills/noaa-sps-skill/SKILL.md)

## Current role

NOAA SPS is the legacy public salmon population-summary web app for ESA-listed demographic data.

## Current posture

- supported: abundance/assessment
- partial: discovery/search, metadata/schema, entity lookup, harvest/fishery, provenance/versioning, bulk-access ergonomics
- missing: identifier crosswalks, telemetry/passage, hatchery, genetics/GSI, package/export

## Why it matters

It fills a population-summary gap, but the public surface is still browser-first and should not be treated as a modern API.


## Transport contract

The adapter uses the shared [source transport contract](../../docs/source-transport.md):
explicit HTTPS origins, checked redirects, real final-origin provenance and
typed failures. The synthetic transport tests establish these local behaviors;
they do not establish current service availability.
