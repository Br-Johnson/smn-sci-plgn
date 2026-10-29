# Local Salmon data graph discovery

Canonical platform card: [smn-data-graph](../../registry/platforms/smn-data-graph.json).

Use [graph-discovery](../../skills/graph-discovery/SKILL.md) with the actual local
`salmongraph.discovery.discover` library at commit
`4036bad502ac0319e1207f233386ac7f766de2f6`, Python>=3.13 and PyOxigraph0.5.13.
The source store must already be admitted and the caller must supply the exact
local project/dataset and read binding. Caller attestation does not prove service
ACLs. The plugin provides no hosted API, graph construction or observations query.

The upstream result is forwarded without inventing paths: source authority/version,
native metadata references, direction, pending review and incomplete-proof refusal
remain intact. Exact-IRI discovery excludes pending paths by default. Explicit
scoped-mapping/suggestion modes do not establish identity equivalence. Same labels
never create a join. No source store changes or contributions occur.

Workbench prose disclosure previews remain a separate format and permission
contract; they are not graph admission or publication approval.
