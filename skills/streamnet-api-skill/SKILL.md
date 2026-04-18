---
name: streamnet-api-skill
description: Query the documented StreamNet REST API for coordinated-assessment tables and records. Use when a user needs StreamNet data or StreamNet schema details and an API key is available.
---

## Operating rules

- Use `scripts/streamnet_api.py` for StreamNet API calls.
- Prefer read-only `tables`, `table`, and `records` actions.
- Expect `STREAMNET_API_KEY` for most real calls.
- Return compact summaries unless the user explicitly asks for raw JSON.
- If the user has no key, explain that the scaffold is ready but the live API requires authentication.

## Input

- Read one JSON object from stdin.
- Required field: `action`
- Supported actions:
  - `tables`
  - `table`
  - `records`
  - `request`
- Optional fields:
  - `table_id`
  - `record_id`
  - `params`
  - `page`
  - `per_page`
  - `agency`
  - `updated_since`
  - `api_key`
  - `timeout_sec`
  - `save_raw`
  - `raw_output_path`

Example:

```bash
echo '{"action":"tables"}' | python skills/streamnet-api-skill/scripts/streamnet_api.py
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
