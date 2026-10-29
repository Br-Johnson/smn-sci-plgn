---
name: salmon-workbench-skill
description: Inspect a local salmon research project export, assess contribution readiness, and prepare an explicitly selected disclosure-review preview. Use with workbench JSON exports; no hosted API or publication is implemented here.
---

# Private research workbench

Read `salmon-research-project.v1` exports from the research workbench. They contain
private project notes, source decisions and identifiers. An export is not a
public contribution, an SDP, a graph release or a scientific approval.

Run Python 3.10+ with the helper in this skill's directory:

```sh
python3 scripts/workbench_bundle.py inspect --bundle project.json --as-of 2026-10-24
python3 scripts/workbench_bundle.py framework-template --bundle project.json
python3 scripts/workbench_bundle.py contribution-preview --bundle project.json --sanitized selected-fields.json
```

Paths above are relative to this skill directory. In Claude Code use
`${CLAUDE_SKILL_DIR}/scripts/workbench_bundle.py`; in Codex use the installed
skill's actual path. The helper reads local files and prints JSON; it does not
write, fetch, upload, call a model, apply decisions or publish.
Install the complete plugin checkout: the wrappers require its shared
`scripts/workbench_project.py`, rather than a copied standalone skill folder.

- Unsaved browser drafts (revision zero, possibly blank owner/timestamps) and
  drafts without a contribution commitment can be inspected. Inspection reports
  unsaved status without establishing an owner or persistence. Saved revision
  records require nonblank owner and valid timestamps; the helper does not
  independently verify server persistence. A contribution preview requires a
  saved revision, commitment, selected output types, reason and finite date.
- Source decisions other than `candidate` require a nonblank reason.
- Optional `domainModel` and `annotationDraft` fields receive private readiness
  counts against the pinned schemaVersion 1 export profile. Missing choices and
  stale recorded source bindings remain review work. A recorded vocabulary pin
  is not verified, and a populated choice is not an accepted scientific meaning.
  Unknown shapes and versions stay uninterpreted; no optional text, IRIs, hashes
  or native column names enter the counts or contribution preview. See
  `docs/research-workbench-contract.md` in the plugin checkout for exact limits.
- An expired embargo becomes `review_due`; visibility stays private. Dates use
  explicit `--as-of` or the export timestamp, never an implicit current clock.
- `selected-fields.json` must contain only explicitly supplied sanitized text
  chosen from `title`, `question`, `description`, `hypothesis`, `region`,
  `spatialScale`, `temporalScale`. Nothing is copied automatically. Do not put
  private notes, IDs, samples, code values or source examples there. The output
  still requires disclosure, rights and attribution review.
- Identity records remain pending or rejected, including published source
  relationships. Source inclusion is not biological equivalence. No RDF bridge
  is written. Preserve lexical aliases, native authority IDs and source versions.

For an explicit analytical framework use `salmon-research-framework-skill`.
For an actual SDP use `metasalmon-skill` and its implemented capabilities;
this helper does not validate SDP contents. If asked to use a workbench API,
report that only the file contract is implemented here. No user credentials or
private artifacts are sent to a third party by these tools.
