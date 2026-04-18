# Skill Graph Maturity Gap

Related concept:
- [Skill graph method](../concepts/skill-graph-method.md)

Related register:
- [docs/platform-gap-register.md](../../docs/platform-gap-register.md)

The repo now has a typed skill graph, but graph-driven routing is still only partially mature.

What is closed:
- stable node IDs for skills, platforms, lanes, and governance tags
- typed edge relations with evidence references
- router guidance for seed-first then graph-expansion selection
- validation that the graph covers the current skills and platform map
- an executable selector with fixture-backed routing cases
- basic auth-state pruning for no-auth requests via platform `access_tier`

What is still open:
- capability-aware ranking instead of purely heuristic selection
- richer auth-state-aware pruning for project-gated or mixed-access sources
- graph updates triggered by new skills before they drift from the router instructions

This is no longer a missing concept, but it is still a maturity gap.
