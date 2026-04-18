# Ontology vs Identity

The ontologies are necessary, but they do not replace an operational identity graph.

## What the ontologies are for

- defining classes and properties for salmon entities, identifiers, mappings, provenance, and validity
- defining shared-vs-profile boundary rules
- defining what kinds of mapping assertions are meaningful and safe

## What the identity graph is for

- storing actual stock, unit, site, hatchery, tag-group, and release-group records
- storing aliases, deprecated identifiers, and cross-system mappings
- attaching provenance, confidence, and time/version context to those records

## Why they stay separate

- the ontology repos explicitly follow a schema-versus-data separation
- operational crosswalk rows are mutable and evidence-sensitive
- mapping records need review states and temporal validity that change faster than ontology terms

## Practical rule

Extend the ontologies when the model is missing.

Do not push live operational crosswalk rows into the ontology TTL files.

Related:
- [Crosswalks and provenance](crosswalks-and-provenance.md)
- [Identity graph gap](../gaps/identity-graph-gap.md)
- [SMN ontology](../platforms/smn-ontology.md)
- [GCDFO ontology](../platforms/gcdfo-ontology.md)
