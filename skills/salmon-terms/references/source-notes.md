# Source Notes

These notes carry over what is still true from the retired `smn` and `gcdfo`
lookup skills. The parts that described how the plugin fetched and parsed the
published JSON-LD were dropped, because metasalmonpy now does the fetching and
parsing.

## smn: the shared Salmon Domain Ontology

- Namespace root: `https://w3id.org/smn`. Term IRIs take the form
  `https://w3id.org/smn/<LocalName>`, for example `https://w3id.org/smn/Escapement`.
- Upstream: [salmon-data-mobilization/salmon-domain-ontology](https://github.com/salmon-data-mobilization/salmon-domain-ontology).
- The first place to look for cross-organization, policy-neutral terms.

## gcdfo: the DFO Salmon Ontology

- Ontology root: `https://w3id.org/gcdfo/salmon`. Term IRIs take the form
  `https://w3id.org/gcdfo/salmon#<LocalName>`, for example
  `https://w3id.org/gcdfo/salmon#ConservationUnit`.
- Upstream: [dfo-pacific-science/dfo-salmon-ontology](https://github.com/dfo-pacific-science/dfo-salmon-ontology).
- For concepts that are DFO-specific, program-scoped, or deliberately
  profile-scoped.

## The boundary between them

- If an approved shared `smn` term exists, use it. Do not select or mint a
  DFO-specific replacement for a concept `smn` already covers.
- If a concept is clearly DFO-specific, look in `gcdfo` rather than forcing it
  into `smn`.
- metasalmonpy ranks `smn` above `gcdfo` for otherwise equal candidates, and
  metasalmon does the same. That ordering comes from the package, so this skill
  does not apply it a second time.

## What this skill is not

It finds terms. It does not resolve operational identity. Mapping a
Conservation Unit to an ESU, or a stock name to a site, is crosswalk work, and
an ontology term is not a crosswalk row.
