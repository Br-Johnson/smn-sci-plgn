# Synthetic ontology-release fixtures

The two RDF/XML files are copied byte for byte from metasalmonpy v0.6.0,
commit `58aff2363519693345d4efdebe8a2027d948f6ce`:

- [smn fixture](https://github.com/salmon-data-mobilization/metasalmonpy/blob/58aff2363519693345d4efdebe8a2027d948f6ce/tests/data/ontology_release/smn-0.0.3/smn.owl)
- [gcdfo fixture](https://github.com/salmon-data-mobilization/metasalmonpy/blob/58aff2363519693345d4efdebe8a2027d948f6ce/tests/data/ontology_release/gcdfo-0.0.9/gcdfo.owl)

They are small synthetic conformance snapshots, not complete published
ontology releases. Their declared version IRIs test the existing released
package's file contract; the tests make no scientific approval claim.

`MANIFEST.sha256` files were added for checksum controls. Expected hashes:

- `smn.owl`: `465b54743a7283dac960ff70c33a71dcb3c505ecd66363690638e4ae56e02ac1`
- `gcdfo.owl`: `f5420bc2565a465b5b0a67e8bafd0cd6c195245acb84d5069f606d4df20356c1`

Tests copy these fixtures into temporary directories to remove a manifest or
change bytes. A manifest verification result records a checksum check only.
