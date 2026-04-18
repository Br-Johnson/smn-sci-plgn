---
name: rmis-skill
description: Query the RMIS / RMPC API for release, recovery, location, catch-sample, description, and file records, and fetch the public RMIS version announcement. Use when the user needs coded-wire-tag data or RMIS status information and has RMIS credentials or an RMPC API key.
---

## Operating rules

- Use `scripts/rmis_api.py` for all RMIS calls.
- RMIS data endpoints are authenticated.
- The public `announcement` action works without credentials.
- Prefer small, explicit queries first.
- Use `save_raw=true` for larger result sets instead of pasting them into chat.

## Access model

Two access paths are relevant:

- public RMIS announcement page
- authenticated RMIS / RMPC API at `https://phish.rmis.org`

The API currently supports:
- `xapikey` header
- `Authorization` header with a JWT-style token

You can also retrieve a token using the login endpoint if you have an RMIS email and password.

## Input

- Read one JSON object from stdin.
- Supported actions:
  - `announcement`
  - `login`
  - `release`
  - `recovery`
  - `location`
  - `catchsample`
  - `description`
  - `files`
  - `request`
- Optional fields:
  - `params`
  - `path`
  - `email`
  - `password`
  - `jwt`
  - `auth_mode`
  - `auth_token`
  - `save_raw`
  - `raw_output_path`
  - `timeout_sec`

Examples:

```bash
echo '{"action":"announcement"}' | python skills/rmis-skill/scripts/rmis_api.py
echo '{"action":"release","params":"reporting_agency=ODFW&perpage=5","auth_mode":"api_key"}' | python skills/rmis-skill/scripts/rmis_api.py
```

## Query syntax

The RMIS API uses query-string filters such as:

- `page=2`
- `perpage=10`
- `sort=column|asc`
- `fields=column1,column2`
- `search=value`
- standard comparisons like `brood_year>=2020`

See [references/rmis-access.md](references/rmis-access.md) for the current query model and access notes.
