# Identity Graph Gap

The repo now has a schema and seed data layer for identity/crosswalk records, but it does not yet have authoritative operational coverage.

## Why it stays open

- the normalizer is still alias-based
- platform records do not reconcile across systems automatically
- seed identity records are explicitly non-authoritative

## Where to look

- [Ontology vs identity](../concepts/ontology-vs-identity.md)
- [Crosswalks and provenance](../concepts/crosswalks-and-provenance.md)
- [SMN ontology](../platforms/smn-ontology.md)
- [GCDFO ontology](../platforms/gcdfo-ontology.md)
