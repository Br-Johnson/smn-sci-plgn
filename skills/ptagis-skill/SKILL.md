---
name: ptagis-skill
description: Query documented PTAGIS endpoints for site observations, file listings, validation-code metadata, and report listings. Use when a user needs PIT-tag metadata or PTAGIS-linked observation access and a PTAGIS token is available.
---

## Operating rules

- Use `scripts/ptagis_api.py` for PTAGIS calls.
- PTAGIS uses documented public endpoints, but many useful calls still require authorization.
- Prefer metadata and scoped site-year requests.
- Do not use tag-level lookups for bulk analysis in chat.
- Return compact summaries unless the user explicitly asks for raw payloads.

Credentials come only from the local environment. Never request or accept
passwords, keys or tokens in chat, JSON fields or query parameters. See
[local authentication](../../docs/source-authentication.md) for the user-run
route and the fixed HTTPS origin/redirect policy.

## Input

- Read one JSON object from stdin.
- Required field: `action`
- Supported actions:
  - `site_observations`
  - `interrogation_site_codes`
  - `interrogation_files`
  - `validation_codes`
  - `reports`
  - `report_file`
  - `request`
- Optional fields:
  - `site_code`
  - `project_code`
  - `year`
  - `user_name`
  - `report_name`
  - `domain`
  - `kind`
  - `path`
  - `params`
  - `timeout_sec`
  - `save_raw`
  - `raw_output_path`
  - `raw_stdout` (boolean; only `true` returns the full redacted payload)

## Output

Results default to a preview of at most five rows per collection and 16 KiB of
serialized stdout, with counts, truncation and source provenance. `save_raw`
saves locally while retaining compact stdout. See [source output controls](../../docs/source-output.md)
for preview semantics and typed save failures. Request `raw_stdout: true` only
when the user explicitly needs bulk records in the tool transcript.

Example:

```bash
echo '{"action":"validation_codes","kind":"mrr_projects"}' | python skills/ptagis-skill/scripts/ptagis_api.py
```
