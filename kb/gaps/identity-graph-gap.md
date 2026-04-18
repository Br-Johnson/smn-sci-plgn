# Identity Graph Gap

The repo now has a schema, a bounded Columbia Basin v0 identity slice, and a seed compatibility layer for identity/crosswalk records, but it does not yet have authoritative operational coverage.

## Why it stays open

- the normalizer is still alias-based, with identity hints limited to the bounded Columbia Basin slice
- platform records do not reconcile across systems automatically
- the identity slice is explicitly non-authoritative and intentionally narrow
- there is no production-grade reconciliation or review workflow yet
- coverage does not extend beyond the Columbia Basin v0 slice

## Where to look

- [Ontology vs identity](../concepts/ontology-vs-identity.md)
- [Crosswalks and provenance](../concepts/crosswalks-and-provenance.md)
- [SMN ontology](../platforms/smn-ontology.md)
- [GCDFO ontology](../platforms/gcdfo-ontology.md)
