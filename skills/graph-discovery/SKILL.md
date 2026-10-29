---
name: graph-discovery
description: Find provenance-bearing connections between dataset IRIs in an authorized, already admitted local Salmon graph store. Use for exact semantic references or explicitly requested pending scoped mappings; this is local read-only discovery, not an observation query or contribution workflow.
---

# Local graph discovery

Use the actual `salmongraph.discovery.discover` library to find connections from
the current project's dataset IRIs to other datasets. The helper preserves the
library's complete response: source versions, graph and reifier evidence,
predicate direction, native metadata context and review state. Equal labels do
not join identities. A connection does not establish scientific compatibility.

Read [the local request contract](references/local-discovery.md) before using a
store. Select the user's already admitted, access-appropriate local store and
project dataset binding. Confirm current read permission within the task's
existing authority. The binding records caller confirmation; it does not prove
fresh server ACLs or certify admission. Never discover or open an unrelated
store merely because its path exists.

The adapter needs Python 3.13+ and pins the standalone graph library to commit
`4036bad502ac0319e1207f233386ac7f766de2f6`, including its `pyoxigraph==0.5.13`
dependency. Its installed Python-source digest must match that pin. Run it
with `uv run -q "${CLAUDE_SKILL_DIR}/scripts/graph_discovery.py"`, sending one JSON
request on stdin. In another harness, substitute this skill's actual directory.
Dependency acquisition is separate from a query; the helper never fetches data,
starts a service, constructs a graph or installs into the user's environment.

Start with `include_pending` omitted. The default is exact-IRI discovery over
the reviewed view. Request pending paths only when the research question calls
for them; keep `awaiting_review`, recorded authority and uncertainty visible.
`scoped_mapping` and `suggestion` additionally need explicit `include_pending:
true` and the population family. They describe a recorded directed relationship,
not an inferred equivalence or a transitive mapping.

For each useful path, cite the actual dataset source/version and evidence
returned by the library, including unresolved review state. Native
`tables.method_iri`, `tables.protocol_iri` and `codes.term_iri` paths retain
`match_basis: native_metadata_reference`; they do not prove an observed
procedure, population membership or biological type. Keep such metadata paths
separate from actual observation paths already present upstream.

If `ok` is false, preserve its typed failure. A
`query_status: partial_evidence_refused` contains no usable paths; do not replace
it with catalogue guesses or a full graph dump. The library globally
materializes review context: targeted read limits do not bound total memory or
establish production capacity. Use the existing admitted store's namespace
configuration without reminting identifiers.

The only actions are `runtime` and `discover`. Observation queries, arbitrary
SPARQL, hosted endpoints, graph writes, admission, identity inference and
automatic contribution are outside this skill. Workbench prose disclosure
previews remain separate and cannot be fed into a graph contribution function.
