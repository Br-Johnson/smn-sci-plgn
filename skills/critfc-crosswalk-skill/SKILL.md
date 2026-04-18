---
name: critfc-crosswalk-skill
description: Query the public CRITFC Columbia Basin crosswalk page and ArcGIS REST services for salmon and steelhead pop/unit mapping. Use when a user needs CRITFC crosswalk context or spatial pop/unit lookup and no auth is required.
---

## Operating rules

- Use `scripts/critfc_crosswalk.py` for CRITFC calls.
- Prefer the public project page and ArcGIS REST reads.
- Treat the legacy query and map tools as browse-and-fetch surfaces, not a stable general API.
- Keep summaries compact and do not imply authority beyond the CRITFC crosswalk scope.

## Input

- Read one JSON object from stdin.
- Required field: `action`
- Supported actions:
  - `page`
  - `rest_root`
  - `request`
- Optional fields:
  - `path`
  - `url`
  - `params`
  - `timeout_sec`
  - `save_raw`
  - `raw_output_path`

Example:

```bash
echo '{"action":"rest_root"}' | python3 skills/critfc-crosswalk-skill/scripts/critfc_crosswalk.py
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
