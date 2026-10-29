---
name: salmon-terms
description: Find existing ontology terms and IRIs for salmon concepts with metasalmonpy's role-aware find_terms() at the pinned v0.6.0 release, across the shared smn ontology, the DFO gcdfo profile, and the external vocabularies the package searches (OLS, NVS, QUDT, GBIF, WoRMS, ZOOMA, BioPortal). Use for terms, definitions or role sources, including exact local smn/gcdfo release snapshots with unchanged version, hash and manifest provenance.
---

# Salmon Terms

Term search belongs to metasalmonpy, the Python mirror of metasalmon. This skill
calls the released package and presents what it returns. It does not fetch
ontology files, rank, filter, or re-score anything itself.

## Run it

The adapter needs [uv](https://docs.astral.sh/uv/). Its
script declares one dependency inline,
`metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0`,
and uv installs it into a cached, isolated environment on first use.
uv keeps that environment in its user cache. Where the cache directory isn't
writable, as in some sandboxed runs, set `UV_CACHE_DIR` to a writable
directory first. Dependency acquisition needs network access initially;
latest searches and remote release downloads also need it. Searching an
existing local snapshot makes no ontology-service request.

```bash
echo '{"action":"find_terms","query":"escapement","role":"variable"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
echo '{"action":"find_terms","query":"conservation unit","sources":["gcdfo"]}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
echo '{"action":"sources_for_role","role":"unit"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
echo '{"action":"find_terms","query":"escapement","sources":["smn"],"release":{"smn":"0.0.3"},"snapshot_dir":{"smn":"/path/to/smn-release-0.0.3"}}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/salmon_terms.py"
```

`${CLAUDE_SKILL_DIR}` is this skill's directory. Claude Code fills it in; in any
other harness use the folder that holds this file, which is
`skills/salmon-terms` in a checkout of the plugin.

## Actions

The adapter reads one JSON object from stdin and writes one to stdout.

- `find_terms` (the default): calls `find_terms(query, role=None, sources=None,
  expand_query=True, release=None, snapshot_dir=None)`. `query` is required;
  `role`, `sources`, `expand_query`, `release` and `snapshot_dir` pass through
  to the package. `max_items` (default 10) shortens the list the package already
  ranked, and `total` says how many rows it returned. The supported fields are
  those controls plus `action`, `max_items`, `save_raw` and
  `raw_output_path`; unknown fields are refused as `invalid_input`.
- `sources_for_role`: calls `sources_for_role(role)`, the ordered source list
  a role searches by default.
- `runtime`: the Python and metasalmonpy versions that actually ran, and the pin.

Every response carries `runtime`, so each result records the package version
that produced it. `save_raw` and `raw_output_path` write the full response to a
file, as in the other skills.

Roles are `variable`, `property`, `entity`, `unit`, `constraint`, and
`statistical_modifier`, plus `method` for code values. Omit `sources` and the
package uses the role's default list; an explicit list is a strict allowlist.
Supported source names are `smn`, `gcdfo`, `ols`, `nvs`, `zooma`, `bioportal`,
`qudt`, `gbif` and `worms`. A name or an array of names is accepted; the
package trims, lower-cases and de-duplicates them, dropping null/empty entries.
An unsupported name makes the request fail as `unsupported_source` before any
lookup, including in a mixed supported/unsupported list. This guard covers a
v0.6.0 package defect; it does not add a PSC CV source or change the defaults.

## Latest searches and release snapshots

The package version does not identify the ontology searched. Without `release`
or `snapshot_dir`, sources use their current live surfaces and
`ontology_release` is null. To make a local ontology search repeatable:

- `release` maps `smn` or `gcdfo` to an exact release, for example
  `{"smn":"0.0.3","gcdfo":"0.0.9"}`. Without a local snapshot the package
  downloads that release; it never falls back to latest.
- `snapshot_dir` maps the same names to existing local release directories.
  When `release` names that ontology too, the snapshot's declared version must
  match. The package checks the selected files against `MANIFEST.sha256` when
  it exists. Missing files, a version mismatch or a checksum mismatch return
  the package's refusal as `package_error`, without latest fallback.
- The explicit source allowlist still applies. Only searched ontologies appear
  in provenance; a pin for an unsearched ontology does not pin other sources.
  External sources remain live. For a wholly local repeatable search, restrict
  `sources` to the smn/gcdfo snapshots supplied.

`ontology_release` is the package's unchanged provenance table, serialized as
rows with `ontology`, `version`, `version_iri`, `file`, `sha256`,
`manifest_verified` and `source`. A snapshot without a manifest remains
`manifest_verified: false`; the adapter does not invent verification. Hash and
manifest verification describe the files read, not scientific approval of a
term or the identity of its publisher. The normal ranked results and
per-source diagnostics remain the package's own output.

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

metasalmon v0.6.0 has the same two functions and the same `release` and
`snapshot_dir` controls. Both packages use role defaults when `sources` is
omitted. An explicit source list is useful when matching an existing pipeline:

```bash
Rscript -e 'install.packages("remotes"); remotes::install_github("salmon-data-mobilization/metasalmon@v0.6.0")'
Rscript -e 'library(metasalmon); r <- find_terms("escapement", role = "variable", sources = sources_for_role("variable")); print(head(r))'
```

The two packages agree that `smn` outranks `gcdfo` for otherwise equal
candidates. Beyond that, their rankings are not pinned to each other
(metasalmonpy `PARITY.md`, row 32). Use R when a result has to match an R
pipeline exactly.
