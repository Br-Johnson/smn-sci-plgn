# Sources and Roles

metasalmonpy owns the source list and the per-role defaults. This page is a
reading aid, not a second copy of the logic: confirm the live defaults with
`{"action":"sources_for_role","role":"..."}` before relying on them.

## Source identifiers metasalmonpy 0.5.0 knows

- `smn`: shared Salmon Domain Ontology, `https://w3id.org/smn`
- `gcdfo`: DFO Salmon Ontology, `https://w3id.org/gcdfo/salmon`
- `ols`, `nvs`, `zooma`, `bioportal`, `qudt`, `gbif`, `worms`: external
  vocabularies and registries

## Default source order per role (as observed at v0.5.0)

- no role: `smn`, `gcdfo`, `ols`, `nvs`
- `variable`: `smn`, `gcdfo`, `nvs`, `ols`, `zooma`
- `property`: `smn`, `gcdfo`, `qudt`, `nvs`, `ols`, `zooma`
- `entity`: `smn`, `gcdfo`, `gbif`, `worms`, `bioportal`, `ols`
- `unit`: `qudt`, `nvs`, `ols`
- `constraint`: `smn`, `gcdfo`, `ols`
- `statistical_modifier`: `smn`, `ols`
- `method`: `smn`, `gcdfo`, `bioportal`, `ols`, `zooma`

## Shared-vs-DFO reminder

- Prefer an approved shared `smn` term for reusable, policy-neutral concepts.
- Treat `gcdfo` terms as DFO profile-scoped. Do not promote them to shared
  status in chat; that is an ontology-repo decision.
- When both ontologies return a hit for the same concept, report both and say
  which is shared.

See [kb/concepts/shared-vs-dfo-term-boundary.md](../../../kb/concepts/shared-vs-dfo-term-boundary.md).
