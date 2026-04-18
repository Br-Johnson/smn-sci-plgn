# Governance-Aware Access Gap

Several important sources are technically reachable but operationally gated.

## Why it stays open

- the repo now has normalized `access_tier` on platform cards and the selector can block credentialed routes for no-auth requests
- skills still mostly express runtime auth details through env vars and request parameters
- the repo still lacks richer policy for project-gated or partially public surfaces
- the agent still needs help distinguishing missing data from missing access and missing authorization scope

## Where to look

- [Platform gap method](../concepts/platform-gap-method.md)
- [PTAGIS](../platforms/ptagis.md)
- [RMIS](../platforms/rmis.md)
- [Skill graph method](../concepts/skill-graph-method.md)
