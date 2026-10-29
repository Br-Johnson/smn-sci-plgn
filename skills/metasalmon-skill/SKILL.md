---
name: metasalmon-skill
description: Validate Salmon Data Packages and fetch the salmon ontologies through released metasalmonpy v0.6.0, the Python mirror of metasalmon. Includes a local fictional CSV-to-reviewed-SDP and EML recipe using SDK functions directly, with R as the documented alternative. Use to check or author a package, confirm its runtime, or cache an ontology. For term search use salmon-terms; to judge semantic review packets use sdp-semantic-review.
---

# metasalmon

Salmon Data Package logic lives in two packages that mirror each other:
[metasalmon](https://github.com/salmon-data-mobilization/metasalmon) in R and
[metasalmonpy](https://github.com/salmon-data-mobilization/metasalmonpy) in
Python, both at `v0.6.0`. This skill runs metasalmonpy and returns what it
returns. Do not re-implement package logic in chat or in a script.

## Run it

The adapter needs [uv](https://docs.astral.sh/uv/). Its script declares one
dependency inline,
`metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0`,
and uv installs it into a cached, isolated environment on first use. No R
installation is needed. uv keeps that environment in its user cache. Where
the cache directory isn't writable, as in some sandboxed runs, set
`UV_CACHE_DIR` to a writable directory first.

```bash
echo '{"action":"runtime"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/metasalmon_api.py"
echo '{"action":"validate_salmon_datapackage","path":"path/to/sdp","require_iris":true}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/metasalmon_api.py"
echo '{"action":"fetch_salmon_ontology","url":"https://w3id.org/smn/"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/metasalmon_api.py"
```

`${CLAUDE_SKILL_DIR}` is this skill's directory. Claude Code fills it in; in any
other harness use the folder that holds this file, which is
`skills/metasalmon-skill` in a checkout of the plugin.

## Actions

The adapter reads one JSON object from stdin and writes one to stdout.

- `runtime` (the default): the Python and metasalmonpy versions that ran, the
  pin, and whether `Rscript` and metasalmon are available for the R route.
- `catalog`: this adapter's actions and every function metasalmonpy exports.
- `validate_salmon_datapackage`: `path` is a required string. `require_iris`
  must be a JSON boolean, not a string, number or null. With `require_iris: true`
  the package runs its strict pre-publication check, which fails on any
  remaining `REVIEW:` IRI or placeholder metadata. On failure `error.message` is
  the package's own message and `issues` holds its typed issue table when the
  failure is structural. On success, `semantic_validation` carries the
  package's semantic report.
- `fetch_salmon_ontology`: `url` is required, and `cache_dir` and
  `fallback_urls` are optional. Use `https://w3id.org/smn/` for `smn` and
  `https://w3id.org/gcdfo/salmon` for `gcdfo`. The adapter has no default URL
  because the two packages default to different ontologies (metasalmon to
  `smn`, metasalmonpy to `gcdfo`). It tries no fallback URL unless you pass one.
  Each cache directory holds one ontology at a time under a file name the
  package chooses, so give `smn` and `gcdfo` separate `cache_dir` values to
  keep both.
- `build_review_packet`, `write_assessments` and `ingest_assessments`: the
  semantic review round trip, through the package's
  `write_semantic_review_packet()` and `ingest_semantic_assessments()`. The
  sdp-semantic-review skill drives them and documents their fields; use that
  skill rather than calling them on their own.

After loading the SDK, each response carries `runtime`. Common malformed
controls are refused before SDK loading. `save_raw` must be a JSON boolean;
`raw_output_path`, when supplied, must be a non-empty string or null. With
`save_raw: true`, the full response is written to that path, or
`metasalmon-raw.json` in the current directory when the path is omitted or
null. If saving fails, one JSON response retains the findings and runtime with `ok: false`,
`error.code: raw_output_failed` and `raw_output_path: null`; it does not print
a traceback or filesystem details. `fallback_urls` is an array of non-empty
strings, so one URL string is never treated as individual characters.

## Operating rules

For a complete local authoring exercise, follow the
[fictional CSV-to-reviewed-SDP recipe](references/local-csv-recipe.md). It uses
the released SDK directly, demonstrates strict draft refusal, requires separate
human fixture confirmation, preserves qualifiers/sidecars in a read/write loop,
and produces one local EML export. It adds no JSON adapter action.

- Term search, meaning `find_terms()` and `sources_for_role()`, is the
  salmon-terms skill's job. This adapter answers those two action names with a
  pointer there.
- The adapter never calls the packages' LLM features. Harness judgement of the
  review packet is recommended, followed by the user's separate acceptance.
  The legacy in-package provider route is deprecated in v0.6.0, remains
  available in 0.6.x and is scheduled for removal in v0.7.0.
- Package creation (`create_sdp()`), the review console (`review_semantics()`,
  `accept_suggestion()`, `reject_suggestion()`, `apply_sdp_semantics()`,
  `review_metadata()`, and the `set_sdp_*()` setters), and publication are not
  bridged here yet. Run them with the user in Python or R, following the
  package documentation. Confirming a term in the console is the user's act,
  which is why sdp-semantic-review hands it to them rather than bridging it.
- Report the package's findings as the package states them. Clean strict
  validation (`require_iris: true`) reports package-check success only. Rights,
  disclosure, scientific review and explicit release authorization remain
  separate publication gates; validation creates no human acceptance.

See [references/capabilities.md](references/capabilities.md) for the action
map, what is not bridged, and why this skill runs Python first.

## R alternative

The same calls in metasalmon v0.6.0:

```bash
Rscript -e 'install.packages("remotes"); remotes::install_github("salmon-data-mobilization/metasalmon@v0.6.0")'
Rscript -e 'metasalmon::validate_salmon_datapackage("path/to/sdp", require_iris = TRUE)'
Rscript -e 'metasalmon::fetch_salmon_ontology(url = "https://w3id.org/smn/", fallback_urls = character(0))'
```

Use R when a result has to match an R pipeline exactly. Known behavioural
differences between the two packages are listed in metasalmonpy's `PARITY.md`.
