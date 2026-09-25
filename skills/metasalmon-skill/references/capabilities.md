# metasalmon Skill Capabilities

## Engines

| Engine | Package | Pin | Status |
|---|---|---|---|
| `python` (default) | `metasalmonpy` from `salmon-data-mobilization/metasalmonpy` | `v0.5.0` | canonical |
| `r` (interim) | `metasalmon` from `salmon-data-mobilization/metasalmon` | `0.5.0` | interim until the Foundry `salmon` CLI ships |

The adapter checks the installed version against the pin at `runtime` and
reports `pin_matches`. It never installs anything itself.

## Current supported actions

- `runtime`
- `catalog`
- `fetch_salmon_ontology`
- `validate_salmon_datapackage`

## Moved

- `find_terms` and `sources_for_role` now live in the `salmon-terms` skill,
  which is the single term-lookup surface of this plugin.

## Current intentional limits

- no direct `create_sdp()` bridge from generic chat payloads yet
- no direct issue-submission or publication submission flow yet
- no local package installation step; the skill checks runtime and reports
  what is missing

## Why this skill exists

- `metasalmon` and `metasalmonpy` already implement the package-first
  semantic workflows
- this plugin exposes that engine through a thin adapter and does not fork it
- see [kb/concepts/thin-front-door.md](../../../kb/concepts/thin-front-door.md)
