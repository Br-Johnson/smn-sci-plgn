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

## [2026-09-25] thin-front-door | claude-manifest-0.5.0-repoint-salmon-terms-evals

- Added `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` beside `.codex-plugin/plugin.json`; both manifests share one `skills/` tree and one version (`0.1.0`).
- Repointed the `metasalmon` platform card, KB page, adapter install hints, and README from the retired `dfo-pacific-science/metasalmon` fork (installed `0.1.2`) to `salmon-data-mobilization/metasalmon` `0.5.0` and `salmon-data-mobilization/metasalmonpy` `0.5.0`; the card now carries `pinned_releases`.
- Deleted `scripts/ontology_lookup_common.py`, `smn-ontology-skill`, and `gcdfo-ontology-skill`. Added `salmon-terms`, a thin adapter over metasalmonpy `find_terms()` / `sources_for_role()` run through `uv`.
- Made `metasalmon-skill` Python-first (metasalmonpy through `uv`) with the R runner kept as an interim engine; term lookup actions moved to `salmon-terms`.
- Added `evals/<skill>/` with one `claude plugin eval` case per skill; the validator now requires them.
- Rewrote the static validator: manifest agreement, a thin-front-door contract for adapters (pinned deps, allowed imports, no ontology or ranking logic), eval presence, one-skill-to-many-platform mappings, and release-pin watch surfaces for both packages.
- Skill graph `0.0.2`: `salmon-terms` replaces the two lookup nodes and uses the metasalmon, smn-ontology, and gcdfo-ontology platforms.
- Added the [thin front door](concepts/thin-front-door.md) concept page and updated the gap register, entrypoints, and workflows.
