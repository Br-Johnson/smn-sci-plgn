# Local Commons evidence

Use `search` and `read` when interpreting research, before synthesis. They read
an **already built, authorized local distribution** from the upstream compiler
at the reviewed Commons commit `20cd300512cddf378c3769bd21c4f346bed61046`
(compiler `0.1.0`). This reader does not clone, compile, fetch source URLs,
write cards, or execute distribution code. Keep contribution checks as separate
actions through `commons_card.py`.

Ask for the admitted distribution path and its trusted `catalog.json` SHA-256
from its authorized builder. Use the exact Commons commit and hash for the
research run; the manifest alone is not proof of origin. A different clean
Commons commit can be selected explicitly if its compiler contract is still
`0.1.0`; this does not change the contribution-tools pin. `full` distributions
may contain private evidence. `promote` means the compiler applied its promotion
filter, **not** that this task has permission to transmit or publish the result.
Do not change the build mode to resolve an access failure.

```json
{"action":"search","distribution_dir":"/admitted/local/build","authorized_local_read":true,"expected_commit":"<exact-40-character-commit>","expected_catalog_sha256":"<trusted-64-character-hash>","query":"winter habitat","limit":5}
```

Send this object on stdin to `commons_card.py`, using plain Python for research
(no optional dependencies needed). `query` is a literal phrase, case-insensitive,
searched in card identity, title, description, tags and compiled claim text.
Results sort by card ID; no semantic relevance, equivalence or truth ranking is
inferred. Read one result using `action: "read"` and its exact `card_id` instead
of `query`. Other admission fields remain required. No default directory,
environment fallback or network acquisition is used for research.

The reader verifies the caller-pinned catalog plus the consumed `concepts.jsonl`
and `claims.jsonl` against the catalog and manifest, row counts and build stamps.
It requires a clean Git-derived build. It does not verify unrelated RDF, SSSOM,
Parquet or gap artifacts. The hash binding is not a signature or independent
attestation of the builder. An unavailable source, malformed distribution,
hash/commit mismatch, unsupported compiler or denied admission returns a typed
failure with no card content. Successful empty search remains distinct.

Search returns at most 20 cards (default 10). Read returns at most 20 claims and
the claim count/truncation flag. An answer exceeding 64 KiB is refused, with a
request to narrow the search or inspect admitted artifacts locally; no bulk
payload is emitted. Artifact inputs are capped at 32 MiB each. Use local tools
for larger distributions; this adapter does not silently ignore oversized data.

Cite card path **and Commons commit**, compiled claim ID and section, and each
source's recorded locator/dates. Source IDs connect compiled claims to the
card's source records. These are compiled locators, not invented line/page
numbers. Preserve recorded `generated`, `verified` and `status`; a generated
claim is not a human verification. Staleness is evaluated at retrieval time in
UTC from `stale_after` (unknown stays null). Direct and incoming `contradicts`
relationships and gap conflicts remain visible. Neither side wins by search
order. The current compiler concept view does not expose a derived claim-level
review verdict or all newer verification history; report that limitation rather
than inventing acceptance. Reopen authorized primary material separately when
needed, with its existing permissions.

Keep retrieved private text in the authorized research context. Do not paste it
into public issues, generated public vocabulary sites, contribution previews or
external services. Retrieval grants no scientific review, mapping acceptance,
public-promotion or publication authority.
