---
name: controlled-vocabulary
description: Create and maintain a small SKOS controlled vocabulary with stable W3ID term IRIs, source-backed definitions, immutable local releases and a GitHub Pages website. Use for vocabulary authoring or publication setup; ordinary term lookup belongs to salmon-terms.
---

# Controlled vocabulary

Turn an agreed set of concepts into a maintained, citable vocabulary. The local
helper prepares CSV/JSON authoring inputs, SKOS Turtle and JSON-LD, versioned
snapshots, HTML pages and reviewable publication files. It makes no network call
and performs no registration, GitHub mutation or deployment.

This is a **SKOS concept** workflow. Keep OWL classes, observation schemas, stock
identities and scientific approval separate. Reuse an existing suitable IRI
before minting a new concept; use `salmon-terms` for ecosystem term lookup.

## Choose the authority before authoring

Establish the vocabulary owner, maintainer GitHub contacts, intended public
scope, license, language, namespace candidate and GitHub repository. Preserve an
existing namespace when maintaining a vocabulary. Check current W3ID namespace
collisions, including case variants, before requesting a new one.

The bundled starter uses slash IRIs:

- Namespace: `https://w3id.org/<slug>/`
- Scheme: `https://w3id.org/<slug>/scheme`
- Term: `https://w3id.org/<slug>/concept/<stable-id>`

Do not turn a label change into an IRI change. For an existing hash namespace or
another established layout, retain its contract and adapt its maintained build
instead of migrating identifiers to this starter. W3ID redirects to a website;
it does not host the vocabulary or allocate names merely because files exist.

## Local authoring path

Read [the authoring profile](references/authoring-profile.md) when creating or
editing the JSON/CSV. Choose a new local directory; the helper refuses to replace
an existing directory. It needs Python 3.10+ with no extra runtime packages. A
fictional exercise is:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/controlled_vocabulary.py" init demo-vocabulary --demo
python demo-vocabulary/tools/controlled_vocabulary.py validate demo-vocabulary
python demo-vocabulary/tools/controlled_vocabulary.py release demo-vocabulary
python demo-vocabulary/tools/controlled_vocabulary.py build demo-vocabulary --output demo-site
python demo-vocabulary/tools/controlled_vocabulary.py prepare-publication demo-vocabulary --output demo-publication
```

`${CLAUDE_SKILL_DIR}` is this skill's directory. In another harness substitute
the directory containing this file. For real work, use `init <new-directory>
--config <metadata.json>`, then author `concepts.csv`. The demo is explicitly
fictional and cannot pass the publication-specific validation gate.

Each command prints a JSON result. A validation failure exits nonzero with an
actionable message. A clean result covers this starter's authoring and integrity
profile; it does not establish source truth, ownership, license permission or
scientific approval. The profile is deliberately narrower than general SKOS.

`release` prepares an immutable **local** snapshot. It preserves stable term
IRIs, verifies earlier snapshot hashes and rejects version overwrite or removal
of previously released identifiers. `build` creates a new preview directory and
includes every verified snapshot. Rebuilding identical inputs is deterministic.

## Publication handoff

Read [publication and identifier maintenance](references/publication.md) before
any external action. Run `prepare-publication` with `--w3id-checkout <current
perma-id/w3id.org clone>` to check that local snapshot for a naming collision.
Without it the result explicitly says the collision check was not performed.

The output contains a manual-only Pages workflow, a proposed
`w3id/ids/<slug>/.htaccess` and contact README, and an **unexecuted** HTTP test
plan. Canonical IRIs use invariant 303 redirects to HTML; explicit representation
paths select Turtle or JSON-LD. This starter does not negotiate arbitrary
`Accept` headers or their quality values.

Review the actual generated vocabulary, website, maintenance contacts and
license with the user. Perform only already-authorized repository, Pages or
W3ID actions; obtain any missing authorization immediately before the external
change. Enable/configure Pages and publish the site first, verify its real
status/MIME types, then test and submit the separate W3ID contribution for
maintainer review. A prepared workflow or PR is not a successful deployment or
registration. Record actual URLs and results after each external step.

When maintaining it, keep old IRIs and snapshots, deprecate terms instead of
deleting them, record definition revisions, and mint a new IRI for a change of
meaning. Update W3ID targets when hosting moves and retest existing paths.
Keep maintainer succession/contact information current.

Primary sources and their operational implications are in
[references/sources.md](references/sources.md).
