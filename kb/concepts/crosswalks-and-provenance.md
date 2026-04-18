# Crosswalks and Provenance

Crosswalks need more than a pair of identifiers.

## Minimum fields

The seed schema in [registry/identity-record.schema.json](../../registry/identity-record.schema.json) requires:

- canonical local ID
- entity type
- identifier scheme and value
- mapped target ID
- mapping relation
- source
- confidence
- record status
- valid time or version
- notes

## Why provenance matters

- different systems often use similar labels with different scopes
- some mappings are exact and others are only advisory
- mapping confidence changes as source systems evolve
- a valid mapping today may become stale after an upstream change

## Current posture

- seed records in [registry/identity/seed-crosswalks.json](../../registry/identity/seed-crosswalks.json) are schema scaffolding only
- authoritative production mappings do not exist in this repo yet
- the identity graph remains an open parity blocker

Related:
- [Ontology vs identity](ontology-vs-identity.md)
- [Identity graph gap](../gaps/identity-graph-gap.md)
- [Updating after upstream drift](../workflows/updating-after-upstream-drift.md)
