---
name: metasalmon-skill
description: Validate Salmon Data Packages and fetch the salmon ontologies through the released metasalmonpy package (v0.5.0, the Python mirror of metasalmon), with metasalmon in R as the documented alternative. Use when the user needs to check a Salmon Data Package, confirm which package release is available, or cache an ontology file. For ontology term search use salmon-terms.
---

# metasalmon

Salmon Data Package logic lives in two packages that mirror each other:
[metasalmon](https://github.com/salmon-data-mobilization/metasalmon) in R and
[metasalmonpy](https://github.com/salmon-data-mobilization/metasalmonpy) in
Python, both at `v0.5.0`. This skill runs metasalmonpy and returns what it
returns. Do not re-implement package logic in chat or in a script.

## Run it

The adapter needs [uv](https://docs.astral.sh/uv/). Its script declares one
dependency inline,
`metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0`,
and uv installs it into a cached, isolated environment on first use. No R
installation is needed.

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
- `validate_salmon_datapackage`: `path` is required. With `require_iris: true`
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

Every response carries `runtime`. `save_raw` and `raw_output_path` write the
full response to a file.

## Operating rules

- Term search, meaning `find_terms()` and `sources_for_role()`, is the
  salmon-terms skill's job. This adapter answers those two action names with a
  pointer there.
- The adapter never calls the packages' LLM features. LLM review in
  metasalmon and metasalmonpy is opt-in, and turning it on is the user's choice,
  made in the package directly.
- Package creation (`create_sdp()`), the 0.5.0 review flow (`review_semantics()`,
  `accept_suggestion()`, `reject_suggestion()`, `apply_sdp_semantics()`,
  `review_metadata()`, and the `set_sdp_*()` setters), and publication are not
  bridged here yet. Run them with the user in Python or R, following the
  package documentation.
- Report the package's findings as the package states them. A clean strict
  validation (`require_iris: true`) is the bar for calling a package ready to
  publish.

See [references/capabilities.md](references/capabilities.md) for the action
map, what is not bridged, and why this skill runs Python first.

## R alternative

The same calls in metasalmon v0.5.0:

```bash
Rscript -e 'install.packages("remotes"); remotes::install_github("salmon-data-mobilization/metasalmon@v0.5.0")'
Rscript -e 'metasalmon::validate_salmon_datapackage("path/to/sdp", require_iris = TRUE)'
Rscript -e 'metasalmon::fetch_salmon_ontology(url = "https://w3id.org/smn/", fallback_urls = character(0))'
```

Use R when a result has to match an R pipeline exactly. Known behavioural
differences between the two packages are listed in metasalmonpy's `PARITY.md`.
