# Local discovery request

The caller selects an already admitted local Oxigraph store and the dataset
IRIs for the current project. Create or select a local JSON binding within the
user's authorized task. No remote source is acquired, and existence of a path
does not establish permission. A wholly fictional binding is:

```json
{
  "store_dir": "admitted-fictional-store",
  "project_datasets": ["https://example.test/fictional/project/dataset"],
  "admitted": true,
  "read_authorized": true
}
```

These are exactly the four binding fields. `store_dir` is an existing local
directory, relative to the binding file or absolute. `project_datasets` contains
1..128 absolute IRIs. The booleans record the caller's admission and current
read-permission confirmation, not independently verified service ACLs. A caller
must not assert them for an unauthorized store. The adapter returns that
limitation and the exact binding file's SHA-256. It does not disclose the local
path in a successful result.

Supply `binding_file` in the request or select it using `SALMON_GRAPH_BINDING`.
Project datasets and store paths cannot be overridden in request fields.
Requests and binding files are limited to 65,536 bytes each. An absent,
unreadable, denied or missing-store binding returns a typed unavailable result;
the helper does not create or acquire a replacement.

```json
{
  "action": "discover",
  "binding_file": "fictional-binding.json",
  "families": ["measurement", "procedure", "population"],
  "include_pending": false,
  "limit": 50
}
```

Optional query controls are forwarded unchanged to the pinned library:

| Field | Supported value |
| --- | --- |
| `families` | Nonempty subset of `measurement`, `procedure`, `population`; all three by default. |
| `graphs` | Absolute named-graph IRIs for display filtering; omission preserves all. Filters are not ACLs and cannot hide global review context. |
| `include_pending` | Boolean, false by default. |
| `limit` | Integer 1..100, default 50. The library preserves `has_more`. |
| `relationship_kinds` | Nonempty subset of `exact_iri`, `scoped_mapping`, `suggestion`; omission keeps the original exact-IRI response. |

The last two relationship kinds require `include_pending: true`; upstream also
requires the population family to discover them. Their result has an actual
`relationship` (subject, predicate, object, original direction, source context),
never a fabricated `shared_iri`. Reverse discovery preserves the same recorded
direction. Source review does not confer shared graph acceptance.

`{"action":"runtime"}` requires no binding and inspects only the installed
package. The PEP 723 requirement pins the public `python/` subproject at commit
`4036bad502ac0319e1207f233386ac7f766de2f6`. A SHA-256 of its complete sorted
`salmongraph/**/*.py` source inventory also guards matching local wheel installs;
the source digest is computed from compact sorted JSON mapping relative paths
to file SHA-256 values. Required digest:
`70b0ed91edb72a92f8b5e413909599a1c444de65fba864e155dcda353935308f`.
The adapter refuses source, version or PyOxigraph mismatches before a query.
This verifies installed source bytes, not scientific correctness or artifact
signing. It makes no claim that distribution version `0.1.0` alone identifies
the reviewed commit.

Upstream configuration is preserved. When a store uses non-default namespaces,
set its existing `SALMONGRAPH_BASE`, `SALMONGRAPH_PROFILE_BASE` and
`SALMONGRAPH_SDPV_NS` environment values before invoking the helper. Runtime
output reports the resolved namespace values. The adapter does not rewrite
configuration or migrate an existing store.

Success wraps the complete library object in `result`, with `runtime` and
`binding` provenance. `result` includes unchanged paths, source authority and
version, review and assertion state, complete native-reference context, evidence
and query limits. Successful empty results remain `ok: true`. An upstream
`partial_evidence_refused` becomes `ok: false` / `incomplete_evidence` while its
original response stays available unchanged. Other fixed errors distinguish
binding unavailability, invalid controls, missing/mismatched runtime and graph
failure. No exception text or raw store contents are emitted as diagnostics.

The source store opens through upstream `ox.Store.read_only`. Global review
still costs O(total store); targeted limits alone do not bound native memory,
execution time or concurrent-service capacity.

Primary implementation and documented contract:
[standalone library README](https://github.com/salmon-data-mobilization/smn-data-graph/blob/4036bad502ac0319e1207f233386ac7f766de2f6/python/README.md),
[discover API](https://github.com/salmon-data-mobilization/smn-data-graph/blob/4036bad502ac0319e1207f233386ac7f766de2f6/python/src/salmongraph/discovery.py).
