# Skill-Graph Routing

Use this file after a broad request has been seeded into 1 to 3 likely lanes.

Canonical graph artifacts:
- [registry/skill-graph.json](../../../registry/skill-graph.json)
- [registry/skill-graph.schema.json](../../../registry/skill-graph.schema.json)
- [platform cards](../../../registry/platforms/)

## Routing pattern

1. Seed candidate lanes from the user's wording.
   Use explicit source names, domain nouns, unit-system names, and verbs such as `validate`, `compare`, `track`, `find`, or `define`.
2. Normalize the entities before expansion.
   Use `salmon-entity-normalizer-skill` for species, jurisdictions, and management-unit systems.
3. Expand through the graph.
   - Follow `routes_to` edges from the router to seeded lanes, then from lanes to candidate skills.
   - Add `depends_on` skills when the lane needs prerequisite normalization or semantics.
   - Add `compose_with` skills only when the question needs corroboration, mixed-source context, or a known companion surface.
   - Resolve `uses_platform` edges back to the platform cards when auth, capability status, or governance constraints matter.
4. Filter the candidate subgraph.
   - Prefer the smallest connected set that answers the actual question.
   - Drop skills whose platform cards are clearly `missing` for the needed capability.
   - Distinguish `missing`, `gated`, and `unsupported by current credentials`.
   - If the graph shows only literature for a lane, say the wrapper coverage is still thin.
5. Decide on coordination.
   Use subagents only when seeded lanes expand into independent evidence branches.

## Current graph policy

- The graph is routing topology, not an identity graph.
- Platform cards remain the canonical source for capability and auth truth.
- The seed normalizer is scaffold-only and must not be treated as authoritative crosswalk coverage.
- `gcdfo` remains a profile layer and should stay paired with `smn` when the user is not asking for DFO-only semantics.

## Maintenance rule

If you add a source skill, change a lane, or change which skills pair together, update the graph and the relevant platform card or KB page in the same change.
