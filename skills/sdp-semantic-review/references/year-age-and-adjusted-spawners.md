# Year, age and adjusted-spawner review

Use these examples when a packet includes year/age coordinates or adjusted
female-spawner estimates. They are role distinctions grounded in source-pinned
models, not new shared vocabulary or scientific approval. Judge the complete
variable before choosing individual slots. Preserve unknowns and ask for the
missing observation, procedure or scope information.

| What the field means | Keep distinct | Review or handoff |
|---|---|---|
| Parental spawning-year basis | `smn:BroodYearBasis` is a SKOS basis concept; `smn:broodYear` is a coordinate predicate; `2019` typed `xsd:gYear` is a coordinate value. | A fixed basis may qualify a variable. A row-varying coordinate needs its data dimension. Neither fills the other's role. Do not put the basis into a measured-characteristic slot. |
| Age | Notation (Gilbert–Rich or European), reference basis (return, maturity or sampling), represented component (total, freshwater or ocean), and age-class value are separate. | Do not decompose `42` into ages 4 and 2 without the declared notation. A value such as `AgeClassValue3` does not identify its basis or component, and is not a brood cohort. |
| Effective Female Spawners | The exact PSC variable `PSC-CV-000035` represents a female-abundance estimate adjusted for eggs not spawned. Its measured characteristic, result category and procedure have separate roles. | Preserve adjustment, sampling, expansion, imputation and uncertainty provenance. A raw female count cannot replace adjusted EFS. In a synthetic example, raw abundance 100 and spawned fraction 0.5 produce EFS 50; this is not a reconstruction of a real stock-year. |
| Unknown method | A measure's name does not identify the sampling or calculation procedure used for a particular dataset. | Keep `method_iri` unresolved and describe the missing procedure. An enumeration candidate does not become correct because the measure concerns abundance. |
| Result versus variable | An OWL measurement-datum class describes a result category. A compound profile SKOS variable identifies the precise quantity. `smn:Abundance` is the reusable characteristic. | Do not turn a result class into a SKOS variable, or assert that all results in one class are comparable. Preserve source native types. |
| Female value reused from NERC/BODC | S10 `S102` version 2 describes specimens in a **sample** identified as female. It is not the PATO female OWL quality class or a Darwin Core sex predicate. | Explicitly include `nvs` in source discovery when needed; role defaults may omit it. Keep version, receipt and sample scope. Applying it to a female spawning-stock component is a domain-reviewed interpretation; use a variable-scoped constraint rather than asserting equivalence or a global constraint on every stock. |
| Mapping evidence | Broad, close and related matches have their recorded direction and scope. | They support discovery, not automatic equivalence, migration or canonicalization. Cross-kind class/concept/property roles still require review. |

PSC alpha.6 retains the original EFS definition and **provisional,
domain-review-pending** status. A prototype-accepted mapping or an accepted
packet choice does not change that status. The draft `smn:UnspawnedEggAdjustment`
and `smn:SpawnerAbundance` remain **unminted proposal names**, outside normative
imports, published term indexes and releases. Do not insert them into a
released shortlist, invent their availability, or substitute a new female term.
Keep a descriptive unknown/proposal and hand it to the owning domain review.

The released package checks structural role/evidence rules and candidate
membership. It cannot establish all these scientific distinctions. In
particular, two candidates may both satisfy a generic `constraint` role while
one is the wrong age component; a raw count can satisfy a generic variable
role while being the wrong adjusted quantity. A package ingestion pass is not
biological approval. The user's confirmation and any required domain approval
remain separate from the harness judgement and strict package conformance.

## Source pins

- Shared year/age roles: [SDO ADR-0002 at e1ed704](https://github.com/salmon-data-mobilization/salmon-domain-ontology/blob/e1ed7049009ee6bbf9a23794fd744f1062cf78e7/docs/adr/0002-year-age-basis-dimensions-and-abundance.md).
- EFS draft scope, source references and NERC application limitation:
  [SDO proposal at the same commit](https://github.com/salmon-data-mobilization/salmon-domain-ontology/blob/e1ed7049009ee6bbf9a23794fd744f1062cf78e7/docs/proposals/2026-10-28-efs-bridge/README.md).
- PSC `v0.1.0-alpha.6`, authoring commit
  `7040f2716dffb47f830895b10b9f3e47e50168b1`; public PSC stock-recruit
  documentation, Table 3 p. 9, field `total_broodyr_EFS`, is cited by that proposal.
  This fixes the reviewed source state; it is not a claim of biological admission.
- NERC/BODC [S102 version 2](http://vocab.nerc.ac.uk/collection/S10/current/S102/2/),
  source date 2013-11-12; preserved receipt in the pinned SDO proposal,
  SHA-256 `b0e884a4593d9791df61f8f1c7dacbe650c90a30637f9e3dbfc1fac6087d35ff`.

## Deterministic controls

`evals/sdp-semantic-review/replay_role_boundaries.py` consumes hand-authored
synthetic cases from `role-boundaries/cases-v1.json`, using the actual pinned
metasalmonpy `v0.6.0` API, plugin answer writer and existing Theme A oracle.
It checks packet fingerprints, recorded candidate provenance, correct outcomes
and deliberately wrong answers, with vocabulary search disabled. It applies no
metadata, submits no requests and invokes no provider. The fixture names and
oracle decisions are examples for review, not an operational term index or a
new scientific validator. They do not measure model quality; no live model run
is claimed. Existing recorded Theme A model cohorts remain separate.
