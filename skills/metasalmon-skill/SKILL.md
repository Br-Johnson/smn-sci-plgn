---
name: metasalmon-skill
description: Run a thin set of package-first salmon data-package and semantic workflows through the `metasalmon` R package. Use when the user needs role-aware term search, ontology fetch, or Salmon Data Package validation rather than raw ontology browsing.
---

## Operating rules

- Use `scripts/metasalmon_api.py` for all package interactions.
- Treat `metasalmon` as the current canonical Salmon Data Package engine. Do not re-implement its logic in chat.
- Start with `runtime` if you are unsure whether the package is installed.
- Use `catalog` to see the currently supported action surface.
- Use `find_terms` for role-aware term search and `validate_salmon_datapackage` for package checks.
- Do not pretend this skill can yet drive the full `create_sdp()` table-ingest path from chat payloads; that remains future work.

## Runtime expectations

- Requires `Rscript`.
- Requires the `metasalmon` package to be installed in the active R library.
- This environment currently has `Rscript` and `metasalmon`, but the skill should always check at runtime.

## Input

- Read one JSON object from stdin.
- Supported actions:
  - `runtime`
  - `catalog`
  - `sources_for_role`
  - `find_terms`
  - `fetch_salmon_ontology`
  - `validate_salmon_datapackage`
- Optional fields:
  - `role`
  - `query`
  - `sources`
  - `expand_query`
  - `max_items`
  - `url`
  - `path`
  - `require_iris`
  - `save_raw`
  - `raw_output_path`

Examples:

```bash
echo '{"action":"runtime"}' | python3 skills/metasalmon-skill/scripts/metasalmon_api.py
echo '{"action":"sources_for_role","role":"property"}' | python3 skills/metasalmon-skill/scripts/metasalmon_api.py
echo '{"action":"find_terms","query":"escapement","role":"variable","max_items":5}' | python3 skills/metasalmon-skill/scripts/metasalmon_api.py
```

Read [references/capabilities.md](references/capabilities.md) when you need the initial action map or want to know what is still intentionally out of scope.
