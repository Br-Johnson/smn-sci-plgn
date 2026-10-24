# Local research-project contract and component evidence

The canonical helper is `scripts/workbench_project.py`. The two skill wrappers call it; neither reimplements a second workbench or an SDP engine. The app exports:

```text
{ format: "salmon-research-project.v1", exportedAt, project: ResearchProject, sources: SourceRecord[], limitations: string[] }
```

This is a private export. Project notes, source decisions and native IDs stay private. The helper validates the current ResearchProject/SourceRecord field types, source/identity status enums, unique record IDs, timestamps, source-hash syntax when present and contribution commitment. It does not retrieve or verify source bytes. Additional fields remain private, are not interpreted and are not copied into summaries or previews. No URLs or referenced paths are fetched.

## Implemented components

- `inspect`: source-decision counts, pending identity count and embargo review state. Drafts may be uncommitted. Browser exports at revision zero may have blank owner/creation/update fields; they are reported as `unsaved_draft` without minting those fields. Revision greater than zero requires nonblank owner and valid timestamps. Server persistence is not independently verified. Non-candidate source decisions require a nonblank reason. Time is explicit `--as-of` or the export timestamp.
- `framework-template`: an editable proposal with question and scale context; missing scientific evidence stays empty/unknown.
- `framework-check`: field/enum checks plus required explicit age/cohort evidence for first-winter proposals, separate direct-survival evidence, and no probability use from hard/unknown assignments. Evidence strings are not scientifically verified.
- `contribution-preview`: a saved revision and committed project are required. Only caller-supplied text in explicitly allowed fields is emitted; no private fields are copied automatically. It remains disclosure-review-required and cannot publish.

CLI output is JSON on stdout. Inputs are unchanged. The local JSON reader rejects duplicate keys, nonfinite tokens, symlink files and oversized inputs. The helper has no network client, model API, graph writer or publication function.

## Verification and article limits

Run `python3 -m unittest discover -s tests -p 'test_workbench_project.py'` for semantic/privacy/CLI refusal controls, and the full offline suite for regressions. `scripts/validate_scaffold.py` checks discoverability/routing/eval structure; its existing watch-surface checks can access public upstream metadata. Live package-adapter tests and live-model evaluations are separate opt-ins. Do not report unscored eval cases as behavioural results.

Evidence for an article can describe these implemented local components and the tests actually run. It cannot claim biological equivalence, first-winter classification of IYS fish, survival estimation, mortality attribution, fitted models, reduced research cost or publication approval. LSF/BECI inspiration and primary references are in `skills/salmon-research-framework-skill/references/framing.md`.

The existing metasalmon adapter remains at its documented pin and narrow action set; this component does not call it or establish a newer SDK compatibility result. Hosted app API/authentication and future Claude/API integrations require their own actual contracts and tests.
