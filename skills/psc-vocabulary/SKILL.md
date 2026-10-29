---
name: psc-vocabulary
description: Discover PSC vocabulary concepts from an explicitly authorized local catalog and immutable release, verifying their pinned hashes and returning exact definitions, reused identifiers, legacy replacements and review status. Use for PSC-specific term lookup; general ecosystem search belongs to salmon-terms, and vocabulary authoring belongs to controlled-vocabulary.
---

# PSC vocabulary discovery

Use the read-only JSON CLI below. It reads an authorized local export; it never
fetches a source, executes source code, changes a mapping or writes a file.
The plugin ships only synthetic test records, with no private PSC catalog.

```bash
echo '{"action":"runtime"}' | python3 "${CLAUDE_SKILL_DIR}/scripts/psc_vocabulary.py"
echo '{"action":"lookup","source_config":"/path/to/reviewed-source.json","authorized":true,"query":"stock reference"}' | python3 "${CLAUDE_SKILL_DIR}/scripts/psc_vocabulary.py"
```

In other harnesses substitute the directory containing this skill for
`${CLAUDE_SKILL_DIR}`. The helper needs Python 3.10+ and no dependencies.
`PSC_VOCABULARY_SOURCE` can name the local source descriptor instead of
`source_config`. Read [the source contract](references/source-contract.md)
before configuring one; pins must come from a reviewed authorized source,
not be recomputed just to make a mismatched source pass.

`authorized:true` records the user's authorization to read that source; it is
not an access grant or evidence of scientific approval. Do not set it merely
because a path exists. Without authorization the reader returns
`permission_refused`; a missing or unreadable source returns
`source_unavailable`. Neither establishes a missing term or an ontology gap.
Never ask for credentials in chat or put credentials in JSON. Obtain a local
export through the user's permitted access process outside this reader.

Lookup matches the query, without case sensitivity, within the catalog's
verified IRI, label, exact definition and legacy aliases. It preserves catalog
order with no semantic ranking; `max_items` is 1–100 (default 10), while `total`
reports the full number matched. A successful empty result is limited to this
verified release, not all PSC knowledge.

Present `source` pins/version alongside results. Preserve exact definitions
and distinguish source term status, lifecycle, draft context selection,
prototype acceptance, domain review and adoption. `not_asserted` means that
this release supplied no supported explicit promotion record for that term.
It does not mean approval or rejection. A reused result retains the external
IRI and source definition; `legacy_records` and `reuse_decisions` preserve the
old PSC identity and explicit replacement provenance.

`mapping_reviews` are informational, including candidate, rejected, deferred
and accepted states. Their `canonicalizes:false` flag applies even to an
exact-match suggestion. Canonical identity comes only from released identity
records and explicit `concept-reuse.csv`, never mapping confidence or status.
Stock-kind concepts name kinds of reference or grouping, not individual stock
records, membership or effective years. This reader cannot resolve those
records or approve a semantic assignment.
