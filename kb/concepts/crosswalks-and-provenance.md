# Crosswalks and Provenance

Crosswalks need more than a pair of identifiers.

## Minimum fields

The bounded Columbia Basin v0 slice in [registry/identity/columbia-basin-v0.json](../../registry/identity/columbia-basin-v0.json) adds a local identity layer on top of the existing crosswalk scaffold. At minimum, a useful record needs:

- stable local ID
- entity type
- label
- aliases
- scheme definitions
- identifier scheme and value
- mapped target ID
- mapping relation
- provenance
- source
- confidence
- record status
- valid time or version
- notes
- optional `valid_from` and `valid_to` for temporal windows

## Why provenance matters

- different systems often use similar labels with different scopes
- some mappings are exact and others are only advisory
- mapping confidence changes as source systems evolve
- a valid mapping today may become stale after an upstream change

## Current posture

- [registry/identity/columbia-basin-v0.json](../../registry/identity/columbia-basin-v0.json) provides a bounded, non-authoritative Columbia Basin v0 slice
- [registry/identity/seed-crosswalks.json](../../registry/identity/seed-crosswalks.json) remains the compatibility crosswalk view
- the normalizer can surface slice-backed hints, but those hints are not production truth
- authoritative production mappings do not exist in this repo yet
- the identity graph remains an open parity blocker outside the bounded slice

Related:
- [Ontology vs identity](ontology-vs-identity.md)
- [Identity graph gap](../gaps/identity-graph-gap.md)
- [Updating after upstream drift](../workflows/updating-after-upstream-drift.md)
