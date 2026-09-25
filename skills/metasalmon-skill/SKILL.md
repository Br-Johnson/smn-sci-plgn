---
name: metasalmon-skill
description: Run Salmon Data Package engine actions (runtime check, action catalog, ontology fetch, package validation) through the pinned metasalmonpy release by default, or through the installed metasalmon R package as an interim engine. Use when the user needs to validate a Salmon Data Package, fetch the salmon ontology through the package, or check which engine actions are available. For term lookup use `salmon-terms`.
---

## What this skill is

A thin adapter over the Salmon Data Package engine. `scripts/metasalmon_api.py`
marshals one JSON request to the engine and returns the engine's answer as
JSON. It holds no package logic; anything the packages can do is done by the
packages.

- Default engine: metasalmonpy `v0.5.0` (Python), resolved by `uv run` from
  the script's inline metadata. This is the canonical path.
- Interim engine: the `metasalmon` R package `0.5.0`, driven through
  `Rscript`. It exists for environments that already have R and metasalmon
  installed, and it is scheduled to retire once the Foundry `salmon` CLI
  ships. Select it with `{"engine":"r"}` or `METASALMON_ENGINE=r`.

Both engines expose the same actions and the same JSON shape.

## Operating rules

- Use `scripts/metasalmon_api.py` for all engine interactions. Do not
  re-implement package behaviour in chat.
- Run it with `uv run` from the repo root, or with the absolute path to this
  skill directory when the plugin is installed. A bare `python3` cannot
  resolve the pinned dependency.
- Start with `runtime` if you are unsure which engine is available or whether
  the installed version matches the pin.
- Use `catalog` to see the current action surface and the package exports.
- Use `validate_salmon_datapackage` for package checks. A failed validation
  returns `ok: false` with the engine's typed `issues` rows; report them, do
  not summarise them away.
- Term lookup (`find_terms`, `sources_for_role`) moved to the `salmon-terms`
  skill. Requesting them here returns `moved_to_salmon_terms`.
- Do not claim this skill drives `create_sdp()` from chat payloads; that
  remains future work.

## Runtime expectations

- Python engine: requires `uv` and network on first run to build the cached
  environment for the pinned release.
- R engine: requires `Rscript` and `metasalmon` installed in the active R
  library. `runtime` reports `pin_matches` so a drifted install is visible.
- Pins are declared at the top of the script and mirrored in
  `registry/platforms/metasalmon.json`. Bump both together.

## Input

Read one JSON object from stdin.

Supported actions:
- `runtime`
- `catalog`
- `fetch_salmon_ontology`
- `validate_salmon_datapackage`

Fields:
- `engine` (optional): `python` (default) or `r`
- `url`, `cache_dir` (optional, `fetch_salmon_ontology`; the engine default
  applies when omitted)
- `path` (required for `validate_salmon_datapackage`)
- `require_iris` (optional, default `false`)
- `save_raw`, `raw_output_path` (optional)

Examples:

```bash
echo '{"action":"runtime"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py
echo '{"action":"catalog"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py
echo '{"action":"validate_salmon_datapackage","path":"./my-sdp","require_iris":true}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py
echo '{"action":"runtime","engine":"r"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py
```

Read [references/capabilities.md](references/capabilities.md) for the action
map, the engine posture, and what is intentionally out of scope.
