# Local research-project contract and component evidence

The canonical helper is `scripts/workbench_project.py`. The two skill wrappers call it; neither reimplements a second workbench or an SDP engine. The app exports:

```text
{ format: "salmon-research-project.v1", exportedAt, project: ResearchProject, sources: SourceRecord[], limitations: string[] }
```

This is a private export. Project notes, source decisions and native IDs stay private. The helper validates the current ResearchProject/SourceRecord field types, source/identity status enums, unique record IDs, timestamps, source-hash syntax when present and contribution commitment. It does not retrieve or verify source bytes. Optional fields have the limited readiness inspection below; other additional fields remain private and uninterpreted. None of their contents are copied into previews. No URLs or referenced paths are fetched.

## Implemented components

- `inspect`: source-decision counts, pending identity count, optional readiness counts and embargo review state. Drafts may be uncommitted. Browser exports at revision zero may have blank owner/creation/update fields; they are reported as `unsaved_draft` without minting those fields. Revision greater than zero requires nonblank owner and valid timestamps. Server persistence is not independently verified. Non-candidate source decisions require a nonblank reason. Time is explicit `--as-of` or the export timestamp.
- `framework-template`: an editable proposal with question and scale context; missing scientific evidence stays empty/unknown.
- `framework-check`: field/enum checks plus required explicit age/cohort evidence for first-winter proposals, separate direct-survival evidence, and no probability use from hard/unknown assignments. Evidence strings are not scientifically verified.
- `contribution-preview`: a saved revision and committed project are required. Only caller-supplied text in explicitly allowed fields is emitted; no private fields are copied automatically. It remains disclosure-review-required and cannot publish.

CLI output is JSON on stdout. Inputs are unchanged. The local JSON reader rejects duplicate keys, nonfinite tokens, symlink files and oversized inputs. The helper has no network client, model API, graph writer or publication function.

## Optional readiness profile

`scripts/_workbench_readiness.py` observes the optional `domainModel` and
`annotationDraft` schemaVersion 1 shapes in workbench commit
`dfdc7a98b3e3a7ffffe97399419f3c48dbf83932`, from
`web/src/lib/research/{types,domainModel,annotationDraft}.ts`. This is a pinned
export-shape profile, not a claim about the deployed app or its current API.

`optionalReadiness` reports concept/relationship/binding counts, concepts lacking
definition or evidence, annotation counts and missing role/value/term choices.
It counts annotation source bindings whose exact recorded source ID, SHA-256 or
unambiguous column no longer matches the export metadata. It never reads source
bytes. A recorded vocabulary ID and digest produce `vocabularyPinRecorded`,
while `vocabularyVerified` remains false: no catalog membership, selectable-term
status, semantic role, model-reference validity or scientific fitness is checked.
Every recognized shape remains `awaiting_review`, including fully populated or
empty collections. Counts are observations, not a complete validator receipt.

Absent fields report `absent`. Unknown versions, additional fields, oversized
collections or unrecognized shapes report `uninterpreted_version` or
`uninterpreted_shape`; they remain unchanged in the source file. Optional
inspection never emits labels, definitions, native identifiers, vocabulary IDs,
IRIs, hashes, notes or raw values. None of these fields is admitted to contribution
previews, and none grants scientific acceptance or disclosure consent.

## Verification and article limits

Run `python3 -m unittest discover -s tests -p 'test_workbench_project.py'` for semantic/privacy/CLI refusal controls, and the full offline suite for regressions. `scripts/validate_scaffold.py` checks discoverability/routing/eval structure; its existing watch-surface checks can access public upstream metadata. Live package-adapter tests and live-model evaluations are separate opt-ins. Do not report unscored eval cases as behavioural results.

Evidence for an article can describe these implemented local components and the tests actually run. It cannot claim biological equivalence, first-winter classification of IYS fish, survival estimation, mortality attribution, fitted models, reduced research cost or publication approval. LSF/BECI inspiration and primary references are in `skills/salmon-research-framework-skill/references/framing.md`.

The existing metasalmon adapter remains at its documented pin and narrow action set; this component does not call it or establish a newer SDK compatibility result. Hosted app API/authentication and future Claude/API integrations require their own actual contracts and tests.
