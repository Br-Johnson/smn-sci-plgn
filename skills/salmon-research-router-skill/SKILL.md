---
name: salmon-research-router-skill
description: Route broad salmon ecology, conservation, and management-science questions to the right salmon skills, normalize core entities first, and synthesize concise evidence-backed answers. Use when the request is broad, ambiguous, or likely to require more than one source.
---

## Purpose

Use this skill as the default entrypoint for broad salmon questions.

Do not keep the router in the foreground for narrow single-source lookups when a more specific salmon skill already matches the request.

## Operating rules

- Normalize species, jurisdictions, and management-unit systems before deep retrieval.
- Prefer 1 to 3 evidence lanes at a time.
- Use the minimum useful number of downstream skills.
- Parallelize only when the lanes are independent.
- End with the user's actual answer, not a tool inventory.

## Initial bundled skills

- `salmon-entity-normalizer-skill`
- `streamnet-api-skill`
- `ptagis-skill`
- `rmis-skill`
- `dart-query-skill`
- `salmon-literature-skill`

## Lane classification

Start by assigning the request to one or more lanes:

- stock status, abundance, and assessment
- telemetry, migration, and passage
- habitat, watershed, and connectivity
- hatchery, harvest, and management
- genetics and stock identification
- climate and ocean context
- literature, reports, and dataset discovery

See [references/lanes.md](references/lanes.md) for the first-pass routing table.

## Recommended workflow

1. Clarify the user objective.
2. Normalize entities with `salmon-entity-normalizer-skill`.
3. Select the smallest useful source skills.
4. Gather evidence.
5. Reconcile conflicts and caveats.
6. Return a concise synthesis.

## Upstream foundations

Treat these repos as upstream foundations for future skill growth:

- shared ontology: `salmon-data-mobilization/salmon-domain-ontology`
- DFO-specific ontology: `dfo-pacific-science/dfo-salmon-ontology`
- data package and semantic workflow engine: `dfo-pacific-science/metasalmon`

## Subagent guidance

Use subagents only when the work splits naturally, for example:

- telemetry versus literature
- StreamNet versus PTAGIS
- habitat versus climate

Keep these steps with the coordinating agent:

- initial framing
- entity normalization
- final conflict resolution
- final synthesis
