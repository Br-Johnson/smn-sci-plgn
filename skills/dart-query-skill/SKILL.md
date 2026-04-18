---
name: dart-query-skill
description: Navigate and fetch key Columbia River DART query surfaces for passage, PIT observations, river conditions, and hatchery-release context. Use when a user needs DART query entrypoints or metadata about an available DART page.
---

## Operating rules

- Use `scripts/dart_query_catalog.py` for all current DART interactions.
- Treat this as a catalog and page-discovery helper, not a full DART data extractor.
- Prefer `catalog` to discover the right DART surface first.
- Use `page` when the user needs a specific DART query URL or page summary.

## Input

- Read one JSON object from stdin.
- Supported actions:
  - `catalog`
  - `page`
- Optional fields:
  - `name`
  - `path`
  - `timeout_sec`

Example:

```bash
echo '{"action":"catalog"}' | python skills/dart-query-skill/scripts/dart_query_catalog.py
```
