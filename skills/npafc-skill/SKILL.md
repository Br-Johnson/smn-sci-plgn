---
name: npafc-skill
description: Query the public NPAFC CKAN catalogue and statistics pages for dataset metadata, downloads, and salmonid time-series context. Use when a user needs NPAFC catalogue lookups and no auth is required.
---

## Operating rules

- Use `scripts/npafc_catalog.py` for catalogue and statistics reads.
- Prefer public dataset search/show calls before lower-level requests.
- Keep results compact and distinguish catalogue metadata from downloadable resource files.
- Treat the surfaced CKAN API as public and read-only.

## Input

- Read one JSON object from stdin.
- Required field: `action`
- Supported actions:
  - `dataset_search`
  - `dataset_show`
  - `resource_show`
  - `statistics_page`
  - `request`
- Optional fields:
  - `q`
  - `id`
  - `rows`
  - `start`
  - `sort`
  - `url`
  - `path`
  - `params`
  - `timeout_sec`
  - `save_raw`
  - `raw_output_path`
  - `raw_stdout` (boolean; only `true` returns the full redacted payload)

Example:

```bash
echo '{"action":"dataset_search","q":"salmon"}' | python3 skills/npafc-skill/scripts/npafc_catalog.py
```

## Output

- `ok`
- `source`
- `action`
- `url`
- `summary`
- `records`
- `raw_output_path`
- `warnings`


## Transport and provenance

Use the [source transport contract](../../docs/source-transport.md) for allowed
origins, redirect rules, retrieval provenance and typed failures. An unavailable
source is reported separately from a successful empty result; another evidence
lane can continue.
- `output` (preview mode, count, limits and truncation)

Default output is at most five rows per collection and 16 KiB of serialized
stdout. Small resource metadata remains available; dataset results and resource
lists are previews. `save_raw` saves the response locally without duplicating
bulk data into stdout. See [source output controls](../../docs/source-output.md)
for details. Use `raw_stdout: true` only for an explicit user request for bulk
records in the transcript.
