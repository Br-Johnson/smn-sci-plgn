# Local PSC discovery source contract

The inspected `psc-salmon-vocabularies` source at commit
`7040f2716dffb47f830895b10b9f3e47e50168b1` generates schema-2.0
`public/catalog.json` from immutable release CSV/JSON. The catalog is a
separate generated projection, not an artifact listed in the release manifest.
Pin both it and the manifest. The reader supports that catalog schema with
release manifest schema 1.0, not old pre-reuse catalogs or a general RDF API.

Create a descriptor in the authorized local export. Relative paths are
relative to that descriptor; absolute paths also work:

```json
{
  "schema_version": "psc-vocabulary.source/v1",
  "source_ref": "reviewed repository commit or export receipt reference",
  "release_directory": "releases/<explicit-version>",
  "release_version": "<explicit-version>",
  "manifest_sha256": "<reviewed 64-character lowercase SHA-256>",
  "catalog_path": "catalog.json",
  "catalog_sha256": "<reviewed 64-character lowercase SHA-256>"
}
```

These are placeholders for an actual reviewed descriptor, not usable hashes.
The local synthetic example is `tests/fixtures/psc-vocabulary/source.json` in
the plugin checkout. It represents no real PSC terms or approved meanings.

The reader first verifies the manifest pin, then every listed artifact's
SHA-256 and byte length; it refuses duplicate artifact paths, traversal and
artifact symlinks. It separately verifies the catalog pin and checks the
release version, canonical identities, exact labels/definitions/scopes,
source versions/status, aliases, legacy replacement records, contexts and
selections against the manifest-bound inputs. Hashes establish agreement with
a reviewed pin, not authorship, permissions or domain approval. `source_ref`
is the caller's provenance reference, not independently authenticated proof.

Required release inputs are `concepts.csv`, `external-concepts.csv`,
`concept-reuse.csv`, `context-selections.csv`, `working-contexts.json`, and
`external-mapping-review.csv`, all listed in the manifest. The upstream
`src/psc_vocab/catalog.py` supplies the projection contract. Definitions and
source provenance remain verbatim. No ontology download, RDF parsing or
metasalmonpy search is substituted for PSC discovery.

If present and manifest-bound,
`provenance/stock-recruit-measurements/promotion.json` supplies the explicit
`approval_status`, `domain_review_status` and `adoption_status` for its listed
concept IDs. Its historical event release stays distinct from the source
snapshot version. Other concepts return `not_asserted` for those fields.
Draft `selection_status` remains distinct from term source status and
mapping `workflow_status`; none is promoted by the reader.

Response `source` records the version, issued date, release status, manifest
and catalog hashes, artifact count and verification result. Each result
preserves source catalog fields plus identity basis, legacy/reuse records,
mapping reviews and review status. It does not canonicalize input data or
rewrite a user's package. `entity_role:"stock_record"` is explicitly refused.

Errors use `status:"unavailable"` without an empty results list for permission,
access, integrity or source-format failures. Treat unavailable and no matches
as different outcomes. The CLI emits no raw exception diagnostics, source
contents or credentials on failure. Configure new pins deliberately when a
source release changes; do not silently follow `latest` or read authoring data.
