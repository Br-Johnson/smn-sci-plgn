---
name: noaa-sps-skill
description: Fetch the public NOAA Salmon Population Summary (SPS) pages and help docs. Use when a user needs salmon population-summary context and no stable JSON API is documented.
---

## Operating rules

- Use `scripts/noaa_sps.py` for SPS page reads.
- Treat SPS as a legacy, browser-first web application rather than a documented machine API.
- Prefer the public home page and help pages over invented query endpoints.
- Keep summaries compact and note when a request is limited to page retrieval.
- The owner `/sps` path without a trailing slash was readable on 2026-10-29 and
  redirected to a same-origin APEX archive-selection page. The separate
  `metadata` action reads [NOAA's InPort record](https://www.fisheries.noaa.gov/inport/item/17904).
  Page/metadata success does not establish live records or a JSON API. If a
  source fails, keep its typed unavailable result and owner-documentation link;
  do not invent a query endpoint, log in, or automatically acquire data elsewhere.

## Input

- Read one JSON object from stdin.
- Required field: `action`
- Supported actions:
  - `home`
  - `help`
  - `metadata` (owner InPort metadata only)
  - `request`
- Optional fields:
  - `url`
  - `path`
  - `params`
  - `timeout_sec`
  - `save_raw`
  - `raw_output_path`

Example:

```bash
echo '{"action":"home"}' | python3 skills/noaa-sps-skill/scripts/noaa_sps.py
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
