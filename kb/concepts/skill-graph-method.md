# Skill Graph Method

Canonical graph artifacts:
- [registry/skill-graph.json](../../registry/skill-graph.json)
- [registry/skill-graph.schema.json](../../registry/skill-graph.schema.json)

This repo now treats the skill graph as a router-adjacent topology layer.

## What the graph is for

- keep `SKILL.md` lean
- make lane, skill, platform, and governance relations explicit
- support seed-first, expand-second routing
- give maintainers one machine-readable place to inspect skill composition

## What the graph is not

- It is not the salmon identity graph.
- It does not replace [ontology vs identity](ontology-vs-identity.md).
- It does not replace per-platform capability truth in [registry/platforms/](../../registry/platforms/).

## Current routing method

1. Seed 1 to 3 lanes from the user's wording.
2. Normalize entities early.
3. Expand through typed edges:
   - `routes_to`
   - `depends_on`
   - `compose_with`
   - `uses_platform`
   - `constrained_by`
4. Inspect the platform cards before committing to a source skill when auth, capability, or governance matters.
5. Prefer the smallest connected subgraph that still answers the question.

## Design boundary

- `registry/skill-graph.json` is topology.
- `registry/platforms/*.json` is capability and access truth.
- `registry/identity/` is identity and crosswalk scaffolding.
- `kb/` explains the system and records drift, but does not replace the structured contracts.

## Current limit

The graph is curated and useful now, but route scoring and drift detection are still heuristic. See [skill graph maturity gap](../gaps/skill-graph-maturity-gap.md).
