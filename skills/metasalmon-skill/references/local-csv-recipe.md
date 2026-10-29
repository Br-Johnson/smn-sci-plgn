# Local CSV to reviewed SDP and EML

This recipe runs released **metasalmonpy v0.6.0**, not another package engine.
It uses an invented two-row CSV and an explicitly fictional vocabulary. It
never accepts arbitrary research CSVs, searches a remote vocabulary, calls a
provider, uploads data or publishes. The non-unit `example.org` IRIs and source
URLs are illustrative fixture identifiers, not registered terms or retrieved
evidence. Do not reuse these semantic choices for real research.

The Python implementation was checked against release commit
`58aff2363519693345d4efdebe8a2027d948f6ce`. Use the released `[eml]` extra for
PyYAML and lxml. The example's inline dependency pins the same release. With a
prepared uv cache, these commands can run offline; dependency installation is
a separate environment setup step, not a data or provider operation.

## 1. Create the incomplete draft

From the plugin checkout, choose a new output directory:

```bash
uv run --offline skills/metasalmon-skill/examples/local_csv_recipe.py draft /path/to/new-fictional-exercise
```

Or use `python` from an existing isolated metasalmonpy v0.6.0 `[eml]`
environment. The bundled [CSV](../examples/fictional-counts.csv) is copied to
`original.csv` and read with pandas. `create_sdp()` receives a named `counts`
data frame with `seed_semantics=False`, `llm_assess=False` and
`check_updates=False`. Schema source is explicitly `vendored`.

`draft-sdp/` is incomplete on purpose. The recipe calls
`validate_salmon_datapackage(..., require_iris=True)` and reports its actual
refusal, including the missing semantic fields. A successful draft creation is
not strict conformance. The original CSV remains untouched.

## 2. Inspect meaning and affirm only this fictional exercise

Inspect the draft metadata and
[fictional evidence](../examples/fictional-evidence.csv) before continuing:

- The entity is fictional salmon, without stock or population identity.
- The property is a fictional count, the constraint is fictional adults,
  and the statistical modifier is a sum of invented replicate counts.
- The unit is COUNT, which the SDK's existing EML unit crosswalk maps to
  `number`. Its description here is locally authored fixture evidence, not a
  claim that QUDT was queried or independently reviewed.
- A table row is one fictional site-level aggregate; site codes are categorical
  and their SDK-created code rows remain consistent with that role.

The recommended real workflow is **harness judgement of the package's review
packet, followed by a separate human decision**; use
`sdp-semantic-review`. Harness suggestions and a prompt to proceed are not human
acceptance. The legacy in-package provider path (`llm_assess` and associated
`llm_*` options) is deprecated in v0.6.0, remains available in 0.6.x and is
scheduled for removal in v0.7.0. This recipe never enables it.

Only after the human explicitly affirms this bundled fictional fixture:

```bash
uv run --offline skills/metasalmon-skill/examples/local_csv_recipe.py review /path/to/new-fictional-exercise --confirm-fictional-semantics
```

The flag is an explicit affirmation of fixture semantics for this exercise.
Do not set it automatically because a task mentions review, because the draft
exists, or because a model recommended terms. Without it, `review` writes
nothing. For real data, use actual source evidence and owner decisions through
the SDK review console/setters; this fixture flag cannot supply that approval.

## 3. Inspect strict validation, round trip and sidecars

The recipe copies the draft to `reviewed-sdp/`, then calls the real
`set_sdp_dataset()`, `set_sdp_table()` and `set_sdp_column()` setters. Both
`constraint_iri` and `statistical_modifier_iri` are set explicitly from the
fixture. The complete hand-supplied evidence goes to
`write_sdp_semantic_closure()`, which derives the canonical vocabulary and
accepted-selection ledger and computes their hashes itself. A callback refuses
any unexpected vocabulary lookup; no empty search is presented as evidence.

The recipe calls strict SDK validation, copies the reviewed package to
`rewritten-sdp/`, reads it with `read_salmon_datapackage()` and rewrites its
managed core with `write_salmon_datapackage(..., overwrite=True, prune=False)`.
It then validates strictly again. Qualifiers, data, code metadata and review
sidecars survive.

This copy-then-in-place rewrite matters: the read API returns core data frames,
not a portable serialization of every sidecar. Writing those frames to an empty
directory alone does not copy review notes or export mappings. The SDK's normal
in-place writer preserves files it does not own; `prune=True` would remove them
and is deliberately absent here.

## 4. Inspect the one local export

`write_eml_from_sdp()` writes `rewritten-sdp/metadata/eml.xml`, using the
[fixture EML mapping](../examples/fictional-eml-mapping.yml). The closure writer
replaces its pending vocabulary/ledger digests with actual hashes. The exporter
checks the reviewed closure and validates EML with the bundled **EML 2.2.0**
XSD when the required `[eml]` dependencies are present; the recipe reports its
actual validation result.

The mapping deliberately retains `publication.public: false` and
`rights_authorization.status: unconfirmed`. Its declared fixture date and
`status: final` describe export metadata, not a real publication or a rights
decision. Strict conformance, an accepted fixture ledger and XSD success do not
grant scientific, disclosure or publication approval.

Only this EML export is exercised. EDH XML, Darwin Core Data Package and KNB
workflows have their own inputs, review gates and supported profiles; a listed
SDK function is not proof that this recipe exercised it. No KNB credential,
archive, upload or publishing function is called.

## R route and validation evidence

metasalmon v0.6.0 exposes the corresponding `create_sdp()`, `set_sdp_dataset()`,
`set_sdp_table()`, `set_sdp_column()`, `write_sdp_semantic_closure()`,
`read_salmon_datapackage()`, `write_salmon_datapackage()` and
`write_eml_from_sdp()` functions. This executable recipe is Python; it does not
claim an executed R replay. When translating an existing R pipeline, retain
named resources and review evidence, set `seed_semantics = FALSE`,
`check_updates = FALSE` and leave the deprecated provider route disabled. R's
writer argument is `dict`, while Python's is `dict_df`; do not copy keyword
arguments blindly between languages. Review package `PARITY.md` for other
differences.

Regression seam: `tests/test_local_package_recipe.py`. Set
`SMN_RECIPE_PYTHON` to a real v0.6.0 `[eml]` interpreter, and optionally
`SMN_RECIPE_SDP_VALIDATOR` to a separately checked-out
`smn-data-pkg/scripts/validate_package.py`. Its environment needs `jsonschema`;
set `SMN_RECIPE_SDP_PYTHON` if that independent tool uses a separate interpreter.
Tests run the subprocess recipe with
provider/network operations forbidden, verify draft/confirmation refusals,
qualifiers and sidecars, independently validate both completed packages, and
parse the exported file directly against the selected local XSD. Missing SDK or
independent-validator setup is reported as a skip, not a validation pass.

Primary implementation contracts: released
[Python package I/O](https://github.com/salmon-data-mobilization/metasalmonpy/blob/v0.6.0/package_io.py),
[semantic closure](https://github.com/salmon-data-mobilization/metasalmonpy/blob/v0.6.0/semantic_closure.py),
[EML export](https://github.com/salmon-data-mobilization/metasalmonpy/blob/v0.6.0/eml.py),
[provider deprecation](https://github.com/salmon-data-mobilization/metasalmonpy/blob/v0.6.0/semantic_review_deprecation.py),
and the independently maintained
[SDP validator](https://github.com/salmon-data-mobilization/smn-data-pkg/blob/6806319c6e88d14064688be7f981e8735269c558/scripts/validate_package.py).
