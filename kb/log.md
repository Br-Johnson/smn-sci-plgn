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

## [2026-10-10] skill | sdp-semantic-review

- Added `sdp-semantic-review` (tern M-19): the harness judges the semantic review packet that metasalmon or metasalmonpy 0.6.0 writes, and the package ingests, validates and records the answers. It replaces the packages' `llm_assess = TRUE` call, which 0.6.0 deprecates and 0.7.0 removes.
- Added `build_review_packet`, `write_assessments` and `ingest_assessments` to `metasalmon-skill`'s adapter. `write_assessments` builds the answer file and its `.packet-id` sidecar from the packet alone.
- Moved every package pin from `v0.5.0` to `v0.6.0`. Neither package has that tag yet, so the live adapter job fails until both are tagged.
- Added `evals/sdp-semantic-review/replay_theme_a.py`, which replays answer files through the pinned package and scores them on metasalmon's Theme A oracles, vendored with the conformance fixtures, and `cohort/`, three blind runs of the skill on the six Theme A packets, none promoted yet.
- Blind runs against the first draft of the guide passed four of the six cases each. All three rejected a fish-weight property because the column totals it, and named a namespace for the gap the oracle leaves uncertain. A second cohort passed all six in two runs of three; the third named `smn` for that gap. The recorded cohort, against the final guide, passed all six in all three runs and agreed on every slot. Every run judged the six cases the guide was revised against, so the cohort shows the guide carries the oracles' positions, not that it generalizes to other packages.

## [2026-10-15] skill | commons-card

- Added `commons-card` (tern M-21), the citation-ledger skill for the salmon knowledge commons. It runs the commons' own `scripts/okf-check.py`, `scripts/ledger/ledger_table.py` and `scripts/ledger/ledger_check.py --from-card`, and prints its `CONTRIBUTING.md`, all at one pinned commons commit, against the user's clone. It holds no checks of its own.
- The commons is private, so the adapter copies the pinned files out of the clone's git objects into a temporary directory for each call and deletes them afterwards; the plugin carries no commons content. When the clone's copies differ from the pinned ones, every response lists them as drift.
- Added a platform card and wiki page for the commons, its skill-platform mapping, and three skill-graph edges, with a new `governance:private-content` tag.
- The eval case grades that the skill fires, runs its adapter, and reports the pinned commit. The offline tests build a small clone of their own; the live tests run only where `SALMON_COMMONS_DIR` names a real clone, and passed against the commons' main on 2026-10-15.
