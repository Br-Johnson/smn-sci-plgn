---
name: noaa-sps-skill
description: Fetch the public NOAA Salmon Population Summary (SPS) pages and help docs. Use when a user needs salmon population-summary context and no stable JSON API is documented.
---

## Operating rules

- Use `scripts/noaa_sps.py` for SPS page reads.
- Treat SPS as a legacy, browser-first web application rather than a documented machine API.
- Prefer the public home page and help pages over invented query endpoints.
- Keep summaries compact and note when a request is limited to page retrieval.

## Input

- Read one JSON object from stdin.
- Required field: `action`
- Supported actions:
  - `home`
  - `help`
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
