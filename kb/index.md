# Salmon Platform Wiki

Maintainer-first knowledge base for the salmon plugin scaffold.

Canonical structured truth:
- [platform gap register](../docs/platform-gap-register.md)
- [platform registry](../registry/)
- [skill graph](../registry/skill-graph.json)
- [bounded Columbia Basin identity slice](../registry/identity/columbia-basin-v0.json)
- [identity seed records](../registry/identity/seed-crosswalks.json)

## Concepts

- [Ontology vs identity](concepts/ontology-vs-identity.md): why ontologies model identity and mapping semantics but do not replace an operational identity graph.
- [Crosswalks and provenance](concepts/crosswalks-and-provenance.md): minimum record fields and approval rules for cross-system mappings.
- [Shared vs DFO term boundary](concepts/shared-vs-dfo-term-boundary.md): when to use `smn`, `gcdfo`, and profile bridge artifacts.
- [Platform gap method](concepts/platform-gap-method.md): how capability status, evidence, and drift are tracked.
- [Skill graph method](concepts/skill-graph-method.md): how lane seeding, graph expansion, and capability filtering fit together.

## Platforms

- [StreamNet](platforms/streamnet.md)
- [PTAGIS](platforms/ptagis.md)
- [RMIS](platforms/rmis.md)
- [DART](platforms/dart.md)
- [CRITFC crosswalk](platforms/critfc-crosswalk.md)
- [NOAA SPS](platforms/noaa-sps.md)
- [NPAFC](platforms/npafc.md)
- [PubMed](platforms/pubmed.md)
- [SMN ontology](platforms/smn-ontology.md)
- [GCDFO ontology](platforms/gcdfo-ontology.md)
- [metasalmon](platforms/metasalmon.md)

## Gaps

- [Identity graph gap](gaps/identity-graph-gap.md)
- [Governance-aware access gap](gaps/governance-access-gap.md)
- [Behavioral validation gap](gaps/behavioral-validation-gap.md)
- [Deterministic workflow gap](gaps/deterministic-workflow-gap.md)
- [Skill graph maturity gap](gaps/skill-graph-maturity-gap.md)

## Workflows

- [Adding a new platform](workflows/adding-a-new-platform.md)
- [Verifying a platform skill](workflows/verifying-a-platform-skill.md)
- [Updating after upstream drift](workflows/updating-after-upstream-drift.md)
- [Stock brief workflow](workflows/stock-brief-workflow.md)

## Log

- [kb/log.md](log.md): append-only chronology of major knowledge-base and registry changes.
