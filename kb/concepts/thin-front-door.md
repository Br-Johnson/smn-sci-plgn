# Thin Front Door

This plugin is the agent-facing front door over the salmon packages, not a
place where logic lives. The rule comes from the Salmon Science Foundry plan
and the tern spec (PL-1): a skill calls a pinned, released package, CLI, or
engine verb for anything the packages can do, and holds no logic of its own.

## What a skill may contain

- `SKILL.md`: when to use the skill, how to call the adapter, how to read the
  answer, and the limits of the upstream it calls.
- `references/`: reading aids that point at upstream behaviour without
  copying it.
- `scripts/`: one or more adapters that marshal JSON to the upstream and
  return the upstream's answer as JSON.
- `evals/<skill>/` (at the repo root): at least one `claude plugin eval` case
  that shows the skill fires and calls its adapter.

## What an adapter is allowed to do

- read one JSON object from stdin and write one JSON object to stdout
- validate the request shape (required fields, allowed actions)
- call a pinned released package (`metasalmonpy @ ... @v0.5.0` through a PEP
  723 inline metadata block and `uv run`), a pinned CLI, or a documented
  public HTTP endpoint through `scripts/_common.py`
- convert the upstream's return value to JSON without interpreting it
- report runtime facts: installed version, whether it matches the pin, which
  engine answered

## What an adapter must not do

- rank, score, search, or match terms locally
- parse ontology documents (JSON-LD, TTL, OWL, SKOS) or carry RDF vocabulary
  literals
- import ontology or dataframe libraries (`rdflib`, `pyld`, `owlready2`,
  `frictionless`, `pandas`, `numpy`, `networkx`)
- import a shared domain module from `scripts/`; only `scripts/_common.py`
  (stdin/stdout, HTTP, raw-save plumbing) is shared
- depend on an unpinned upstream (`@main`, no version)
- grow past 400 lines; that is the signal that logic is accumulating

## How it is enforced

`scripts/validate_scaffold.py` runs a static check over every
`skills/*/scripts/*.py`:

1. inline PEP 723 dependencies must be pinned to a release, and any pin for a
   package listed in `registry/platforms/metasalmon.json` `pinned_releases`
   must equal the registry pin
2. `PINNED_<PACKAGE>` constants in adapters must equal the registry pin
3. non-stdlib imports must be `_common` or a declared pinned dependency
4. forbidden imports, RDF/JSON-LD literals, and ranking or term-search
   function names fail the check
5. `scripts/ontology_lookup_common.py` must stay deleted
6. every skill must have an eval case with a `tool_used: Skill` grader

The watch-surface checks then compare each pin with the latest upstream
release and warn when the pin is behind.

## Where the seams are today

- `salmon-terms` and `metasalmon-skill` call metasalmonpy `v0.5.0` through
  `uv run`. `metasalmon-skill` also carries an interim R engine that calls
  the `metasalmon` R package at the same pin; it retires when the Foundry
  `salmon` CLI ships.
- The source-platform skills (StreamNet, PTAGIS, RMIS, DART, NPAFC, NOAA SPS,
  CRITFC, PubMed) are HTTP adapters over public or credentialed APIs. They
  stay until the Foundry data-access registry records them as seeded (PL-4).
- `salmon-entity-normalizer-skill` and `salmon-stock-brief-workflow-skill`
  are scaffold-level routing and contract helpers, not platform adapters.
  They are within the line budget and hold no ontology logic, but they are
  the two places most likely to accumulate logic that should move upstream.

Related:
- [metasalmon / metasalmonpy](../platforms/metasalmon.md)
- [Shared vs DFO term boundary](shared-vs-dfo-term-boundary.md)
- [Behavioral validation gap](../gaps/behavioral-validation-gap.md)
