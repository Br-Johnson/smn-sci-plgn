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

## [2026-09-25] evals | per-skill-cases

- Ported the per-skill eval cases from the parallel draft (Br-Johnson/smn-sci-plgn#1) into `evals/`, one case per skill in the `claude plugin eval` format, on Brett's ruling that #2 goes forward with #1's evals.
- Adapted two cases. The router case no longer grades a call to `scripts/skill_graph_selector.py`, which its SKILL.md never asks for; it now grades that no source adapter runs, the prompt's own "plan, don't fetch" constraint. The metasalmon case's engine grader now needs `metasalmonpy` and a version rather than any mention of metasalmon.
- Added `validate_evals()` to `scripts/validate_scaffold.py`, because `claude plugin validate` does not read eval files. It checks the documented case format, requires an eval case for every skill, and fails when a case names a skill or script that no longer exists.
- Added `tests/test_eval_cases.py`, which feeds four cases' deterministic graders the offline output of their skills' scripts. It scores no case.
- No case has been scored. `claude plugin eval` needs Claude Code 2.1.269 or later, and the installed 2.1.267 answers that the command is in early access.
- Measured 2026-09-25: `gis.critfc.org`, the CRITFC skill's REST root, does not resolve, and the NOAA SPS skill's home URL returns 404. Both cases can still pass by reporting the failure honestly.
