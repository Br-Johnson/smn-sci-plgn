---
name: salmon-terms
description: Look up salmon ontology terms, IRIs, and definitions across the shared `smn` ontology, the DFO `gcdfo` ontology, and the external vocabularies metasalmonpy already searches, using metasalmonpy `find_terms()` and `sources_for_role()` through uv. Use when the user needs a term or IRI for a salmon concept, wants to know which sources a semantic role searches, or asks whether a concept is shared or DFO-specific.
---

## What this skill is

A thin adapter over the pinned metasalmonpy release. It holds no ranking,
parsing, or ontology logic of its own: `scripts/salmon_terms.py` marshals one
JSON request to `metasalmonpy.find_terms()` or
`metasalmonpy.sources_for_role()` and returns the package's answer as JSON.

The package does the retrieval, query expansion, role-aware ranking, and
cross-source agreement. If a result looks wrong, the fix belongs upstream in
metasalmonpy, not here.

## Operating rules

- Use `scripts/salmon_terms.py` for every lookup. Do not fetch or parse
  `smn.jsonld`, `gcdfo.jsonld`, or any TTL in chat.
- Run the script with `uv run` from the repo root, or with the absolute path
  to this skill directory when the plugin is installed. Do not run it with a
  bare `python3`; the pinned dependency is declared in the script's inline
  metadata and only `uv run` resolves it.
- Start with `sources_for_role` when you are unsure which vocabularies a role
  searches. Roles are `variable`, `property`, `entity`, `unit`, `constraint`,
  `statistical_modifier`, and `method`.
- Prefer shared `smn` terms for cross-organization, policy-neutral concepts.
  Treat `gcdfo` hits as DFO profile-scoped. When the user asks whether a term
  is shared or DFO-specific, read the `source` column of each result rather
  than guessing.
- Pass an explicit `sources` list when the user wants a strict allowlist, for
  example `["smn"]` for shared-only or `["smn","gcdfo"]` for the two salmon
  ontologies. An explicit list is a strict allowlist inside metasalmonpy.
- Report `diagnostics` when a source did not answer; an empty result with an
  `http_error` diagnostic is not evidence that a term is missing.
- Keep `max_items` small (5 to 10) in chat. Use `save_raw` for larger pulls.

## Runtime expectations

- Requires `uv` (https://docs.astral.sh/uv/). The first run builds a cached
  environment for the pinned release; later runs reuse it.
- Requires network access: metasalmonpy queries the published ontologies and
  external vocabularies live.
- Pinned release: metasalmonpy `v0.5.0` from
  `salmon-data-mobilization/metasalmonpy`. The pin is declared in the script
  header and mirrored in `registry/platforms/metasalmon.json`; bump both
  together.
- `runtime` reports the installed metasalmonpy version and whether it matches
  the pin.

## Input

Read one JSON object from stdin.

Supported actions:
- `runtime`
- `sources_for_role`
- `find_terms`

Fields:
- `role` (optional): semantic role for ranking and default sources
- `query` (required for `find_terms`)
- `sources` (optional): explicit source allowlist
- `expand_query` (optional, default `true`)
- `max_items` (optional, default `10`)
- `save_raw`, `raw_output_path` (optional)

Examples:

```bash
echo '{"action":"runtime"}' | uv run skills/salmon-terms/scripts/salmon_terms.py
echo '{"action":"sources_for_role","role":"property"}' | uv run skills/salmon-terms/scripts/salmon_terms.py
echo '{"action":"find_terms","query":"escapement","role":"variable","sources":["smn"],"max_items":5}' | uv run skills/salmon-terms/scripts/salmon_terms.py
echo '{"action":"find_terms","query":"conservation unit","sources":["smn","gcdfo"]}' | uv run skills/salmon-terms/scripts/salmon_terms.py
```

## Output

- `ok`, `action`, `runtime`
- `sources` for `sources_for_role`
- `results` (rows with `label`, `iri`, `source`, `ontology`, `role`,
  `match_type`, `definition`, `score`, `alignment_only`,
  `agreement_sources`, `role_hints`), `count`, `count_total`, and
  `diagnostics` for `find_terms`
- `error` with `code` and `message` when `ok` is false

Read [references/sources-and-roles.md](references/sources-and-roles.md) for
the default source order per role and the shared-vs-DFO reminder.
