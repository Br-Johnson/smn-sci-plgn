# Knowledge Base Log

## [2026-04-17] bootstrap | registry-and-wiki

- Added `registry/` with platform-card and identity-record schemas.
- Added per-platform cards for the current external-source skill set.
- Added a seed identity/crosswalk data layer that is explicitly non-authoritative.
- Added the maintainer-first `kb/` wiki tree with concepts, platform pages, gaps, and workflows.
- Wired the repo so validation can reason about the registry, wiki, and upstream watch surfaces.

## [2026-04-17] routing | skill-graph-mvp

- Added `registry/skill-graph.schema.json` and `registry/skill-graph.json` as the canonical routing-topology contract.
- Added router guidance for semantic or lexical seeding followed by typed graph expansion.
- Added wiki pages for the skill-graph method and remaining graph-maturity gap.
- Extended validation to enforce graph coverage, typed relations, and consistency against the platform map.

## [2026-04-17] expansion | selector-identity-and-sources

- Added an executable selector plus fixture-backed regression cases and CI wiring.
- Added a bounded Columbia Basin v0 identity slice and normalizer-emitted identity hints.
- Added CRITFC crosswalk, NOAA SPS, and NPAFC source scaffolds with platform cards and KB pages.
- Added a stock-brief workflow scaffold and contract helper.
- Updated the shared docs and gap register so the new routing, identity, access-tier, and workflow layers are first-class.

## [2026-09-25] retirement | thin-front-door

- Retired the plugin's own JSON-LD term search, `scripts/ontology_lookup_common.py`, together with the two skills built on it, `smn-ontology-skill` and `gcdfo-ontology-skill`. The new `salmon-terms` skill calls metasalmonpy's `find_terms()` and `sources_for_role()` at the `v0.5.0` tag instead.
- Repointed the metasalmon platform card, wiki page, and skill from the retired `dfo-pacific-science/metasalmon` fork at 0.1.2 to `salmon-data-mobilization/metasalmon` and `salmon-data-mobilization/metasalmonpy`, both pinned at `v0.5.0`.
- Rewrote `metasalmon-skill` as a Python-first adapter to metasalmonpy with the R route documented as the alternative, and moved its term-search actions to `salmon-terms`.
- Added `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` beside `.codex-plugin/plugin.json`. Validation now checks that the manifests agree, that every referenced skill exists, that the package pins agree, and that no skill script reimplements term search.
- Collapsed the two ontology skills into `salmon-terms` in the skill graph, the skill-platform map, the selector, and its fixtures. A DFO-specific request now keeps `gcdfo` in the term search's sources instead of adding a second skill.
- Measured the watch surfaces the same day: `smn` publishes version 0.0.3 (modified 2026-08-14) and `gcdfo` version 0.0.9 (modified 2026-08-16).
