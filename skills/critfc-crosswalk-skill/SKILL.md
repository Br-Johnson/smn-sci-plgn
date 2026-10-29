---
name: critfc-crosswalk-skill
description: Query the public CRITFC Columbia Basin crosswalk page and ArcGIS REST services for salmon and steelhead pop/unit mapping. Use when a user needs CRITFC crosswalk context or spatial pop/unit lookup and no auth is required.
---

## Operating rules

- Use `scripts/critfc_crosswalk.py` for CRITFC calls.
- Prefer the public project page and ArcGIS REST reads.
- Treat the legacy query and map tools as browse-and-fetch surfaces, not a stable general API.
- Keep summaries compact and do not imply authority beyond the CRITFC crosswalk scope.
- The [owner project page](https://critfc.org/fish-and-watersheds/fishery-science/data-resources/columbia-basin-salmon-and-steelhead-crosswalk-project/)
  was readable on 2026-10-29 and still advertises the legacy GIS host. It marks
  its map tools offline. The last audit REST check failed DNS; no replacement
  was verified or new live GIS query run. Use the project page and its linked
  guide for discovery context. A failed REST result stays unavailable and links
  to that documentation; page success does not establish records or identity.

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


## Transport and provenance

Use the [source transport contract](../../docs/source-transport.md) for allowed
origins, redirect rules, retrieval provenance and typed failures. An unavailable
source is reported separately from a successful empty result; another evidence
lane can continue.
