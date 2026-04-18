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
