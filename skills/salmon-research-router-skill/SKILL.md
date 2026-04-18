---
name: salmon-research-router-skill
description: Route broad salmon ecology, conservation, and management-science questions to the right salmon skills, normalize core entities first, and synthesize concise evidence-backed answers. Use when the request is broad, ambiguous, or likely to require more than one source.
---

## Purpose

Use this skill as the default entrypoint for broad salmon questions.

Do not keep the router in the foreground for narrow single-source lookups when a more specific salmon skill already matches the request.

## Operating rules

- Seed candidate lanes with lexical or semantic cues first, then expand through `registry/skill-graph.json`.
- Normalize species, jurisdictions, and management-unit systems before deep retrieval.
- Prefer 1 to 3 evidence lanes at a time.
- Use the smallest useful connected subgraph of downstream skills.
- Parallelize only when the lanes are independent.
- End with the user's actual answer, not a tool inventory.

## Initial bundled skills

- `salmon-entity-normalizer-skill`
- `smn-ontology-skill`
- `gcdfo-ontology-skill`
- `metasalmon-skill`
- `streamnet-api-skill`
- `ptagis-skill`
- `rmis-skill`
- `dart-query-skill`
- `salmon-literature-skill`
- `critfc-crosswalk-skill`
- `noaa-sps-skill`
- `npafc-skill`
- `salmon-stock-brief-workflow-skill`

## Lane classification

Start by assigning the request to one or more lanes:

- stock status, abundance, and assessment
- crosswalks, reconciliation, and stock-unit harmonization
- telemetry, migration, and passage
- habitat, watershed, and connectivity
- hatchery, harvest, management, and coded-wire-tag
- genetics and stock identification
- climate and ocean context
- ontology and semantic resolution
- literature, reports, and dataset discovery
- Salmon Data Package and metadata validation
- composite stock briefs

See [references/lanes.md](references/lanes.md) for the stable lane IDs and first-pass routing table.
See [references/skill-graph-routing.md](references/skill-graph-routing.md) for graph expansion, capability filtering, and governance-aware selection.

## Recommended workflow

1. Clarify the user objective.
2. Seed 1 to 3 candidate lanes from the request.
3. Normalize entities with `salmon-entity-normalizer-skill`.
4. Expand through the skill graph and select the smallest useful source set, using access tiers to distinguish public from credentialed routes.
5. Gather evidence.
6. Reconcile conflicts and caveats.
7. Return a concise synthesis.

## Upstream foundations

Treat these repos as upstream foundations for future skill growth:

- shared ontology: `salmon-data-mobilization/salmon-domain-ontology`
- DFO-specific ontology: `dfo-pacific-science/dfo-salmon-ontology`
- data package and semantic workflow engine: `dfo-pacific-science/metasalmon`

## Gap awareness

When the user asks what the salmon domain still lacks, or whether the repo is at parity with the Life Science Research plugin, consult `docs/platform-gap-register.md` first and answer from that maintained register instead of improvising.

## Subagent guidance

Use subagents only when the work splits naturally, for example:

- telemetry versus literature
- StreamNet versus PTAGIS
- habitat versus climate
- one seeded lane versus another independent seeded lane

Keep these steps with the coordinating agent:

- initial framing
- entity normalization
- final conflict resolution
- final synthesis
