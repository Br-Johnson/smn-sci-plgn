# metasalmon / metasalmonpy

- Platform card: [registry/platforms/metasalmon.json](../../registry/platforms/metasalmon.json)
- Related skills: [metasalmon-skill](../../skills/metasalmon-skill/SKILL.md), [salmon-terms](../../skills/salmon-terms/SKILL.md)
- Upstream: [salmon-data-mobilization/metasalmon](https://github.com/salmon-data-mobilization/metasalmon) (R) and [salmon-data-mobilization/metasalmonpy](https://github.com/salmon-data-mobilization/metasalmonpy) (Python)
- Pinned releases: metasalmon `0.5.0`, metasalmonpy `0.5.0` (both released 2026-08 / 2026-09; verified 2026-09-25 with `gh api .../releases`)

## Current role

The two packages are the Salmon Data Package engine: package creation,
semantic term search, semantic review, package validation, ontology fetch,
and publication helpers. metasalmonpy mirrors metasalmon's API in Python.

This plugin exposes two thin adapters over them:

- `salmon-terms`: `find_terms()` and `sources_for_role()` through
  metasalmonpy, replacing the plugin's former JSON-LD lookup scripts
- `metasalmon-skill`: runtime and catalog inspection, `fetch_salmon_ontology()`,
  and `validate_salmon_datapackage()`; metasalmonpy by default, the R
  package as an interim engine

## Current posture

- supported: discovery/search, metadata/schema, package/export (validation)
- partial: entity lookup, identifier-crosswalk support, provenance/versioning, bulk-access ergonomics
- missing: direct assessment, telemetry, harvest, hatchery, and genetics workflows in the current adapters

## Repoint history

- Until 2026-09-25 the card pointed at the retired `dfo-pacific-science/metasalmon`
  fork and an installed R version `0.1.2`. The fork's last commit is
  "Retire moved metasalmon fork" (2026-08-05).
- The canonical repositories now live under `salmon-data-mobilization`.
  metasalmonpy is not on PyPI; adapters resolve it from the git tag through
  `uv run` and the script's inline metadata.

## Why it matters

This is the strongest package-first component in the salmon stack. The plugin
exposes it rather than forking it; see [thin front door](../concepts/thin-front-door.md).
