---
name: salmon-terms
description: Find existing ontology terms and IRIs for salmon concepts with metasalmonpy's role-aware find_terms() at the pinned v0.5.0 release, across the shared smn ontology, the DFO gcdfo profile, and the external vocabularies the package searches (OLS, NVS, QUDT, GBIF, WoRMS, ZOOMA, BioPortal). Use when the user needs a term, IRI, label, or definition for a salmon concept, wants a shared or DFO-specific term, or asks which sources a semantic role searches.
---

# Salmon Terms

Term search belongs to metasalmonpy, the Python mirror of metasalmon. This skill
calls the released package and presents what it returns. It does not fetch
ontology files, rank, filter, or re-score anything itself.

## Run it

The adapter needs [uv](https://docs.astral.sh/uv/) and network access. Its
script declares one dependency inline,
`metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0`,
and uv installs it into a cached, isolated environment on first use.

```bash
echo '{"action":"find_terms","query":"escapement","role":"variable"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
echo '{"action":"find_terms","query":"conservation unit","sources":["gcdfo"]}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
echo '{"action":"sources_for_role","role":"unit"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
```

`${CLAUDE_SKILL_DIR}` is this skill's directory. Claude Code fills it in; in any
other harness use the folder that holds this file, which is
`skills/salmon-terms` in a checkout of the plugin.

## Actions

The adapter reads one JSON object from stdin and writes one to stdout.

- `find_terms` (the default): calls `find_terms(query, role=None, sources=None, expand_query=True)`.
  `query` is required; `role`, `sources`, and `expand_query` pass straight
  through. `max_items` (default 10) shortens the list the package already
  ranked, and `total` says how many rows it returned.
- `sources_for_role`: calls `sources_for_role(role)`, the ordered source list
  a role searches by default.
- `runtime`: the Python and metasalmonpy versions that actually ran, and the pin.

Every response carries `runtime`, so each result records the package version
that produced it. `save_raw` and `raw_output_path` write the full response to a
file, as in the other skills.

Roles are `variable`, `property`, `entity`, `unit`, `constraint`, and
`statistical_modifier`, plus `method` for code values. Omit `sources` and the
package uses the role's default list; an explicit list is a strict allowlist.

## Operating rules

- Present the package's results in the package's order. Do not re-rank them,
  and do not drop a result because it looks wrong. Say so instead.
- Prefer a shared `smn` term for cross-organization, policy-neutral concepts.
  For a DFO-specific concept keep `gcdfo` in `sources`, or restrict `sources`
  to `["gcdfo"]` when the user wants DFO terms only. See
  [references/source-notes.md](references/source-notes.md) for the boundary
  rule.
- Read `diagnostics` before calling anything missing. A source with status
  `error` or `http_error` did not answer, so an empty or short result means
  unknown, not an ontology gap. The package also says this in `warnings`.
- BioPortal answers only when `BIOPORTAL_APIKEY` is set in the environment.
  Without it the package skips BioPortal and warns. Never ask for the key in chat.
- A term IRI the user will write into a Salmon Data Package is a semantic
  choice. Say what justifies it besides being the top hit, such as the
  definition matching the column.
- A real gap, meaning no suitable term in any source, goes through the package's
  own pipeline: `detect_semantic_term_gaps()`, `render_ontology_term_request()`,
  then `submit_term_request_issues()`. The last one files GitHub issues, so keep
  it a dry run (its default) until the user has read and approved the rendered
  text.

## R alternative

metasalmon v0.5.0 has the same two functions. R's `find_terms()` defaults to a
fixed source list (`smn`, `gcdfo`, `ols`, `nvs`) whatever the role, so pass
`sources = sources_for_role(role)` to search what this skill searches:

```bash
Rscript -e 'install.packages("remotes"); remotes::install_github("salmon-data-mobilization/metasalmon@v0.5.0")'
Rscript -e 'library(metasalmon); r <- find_terms("escapement", role = "variable", sources = sources_for_role("variable")); print(head(r))'
```

The two packages agree that `smn` outranks `gcdfo` for otherwise equal
candidates. Beyond that, their rankings are not pinned to each other
(metasalmonpy `PARITY.md`, row 32). Use R when a result has to match an R
pipeline exactly.
