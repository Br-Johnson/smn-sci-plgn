# Salmon Platform Wiki

Maintainer-first knowledge base for the salmon plugin scaffold.

Canonical structured truth:
- [platform gap register](../docs/platform-gap-register.md)
- [platform registry](../registry/)
- [identity seed records](../registry/identity/seed-crosswalks.json)

## Concepts

- [Ontology vs identity](concepts/ontology-vs-identity.md): why ontologies model identity and mapping semantics but do not replace an operational identity graph.
- [Crosswalks and provenance](concepts/crosswalks-and-provenance.md): minimum record fields and approval rules for cross-system mappings.
- [Shared vs DFO term boundary](concepts/shared-vs-dfo-term-boundary.md): when to use `smn`, `gcdfo`, and profile bridge artifacts.
- [Platform gap method](concepts/platform-gap-method.md): how capability status, evidence, and drift are tracked.

## Platforms

- [StreamNet](platforms/streamnet.md)
- [PTAGIS](platforms/ptagis.md)
- [RMIS](platforms/rmis.md)
- [DART](platforms/dart.md)
- [PubMed](platforms/pubmed.md)
- [SMN ontology](platforms/smn-ontology.md)
- [GCDFO ontology](platforms/gcdfo-ontology.md)
- [metasalmon](platforms/metasalmon.md)

## Gaps

- [Identity graph gap](gaps/identity-graph-gap.md)
- [Governance-aware access gap](gaps/governance-access-gap.md)
- [Behavioral validation gap](gaps/behavioral-validation-gap.md)
- [Deterministic workflow gap](gaps/deterministic-workflow-gap.md)

## Workflows

- [Adding a new platform](workflows/adding-a-new-platform.md)
- [Verifying a platform skill](workflows/verifying-a-platform-skill.md)
- [Updating after upstream drift](workflows/updating-after-upstream-drift.md)

## Log

- [kb/log.md](log.md): append-only chronology of major knowledge-base and registry changes.
