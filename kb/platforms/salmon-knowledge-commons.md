# Salmon Knowledge Commons local tools

- Platform card: [registry/platforms/salmon-knowledge-commons.json](../../registry/platforms/salmon-knowledge-commons.json)
- Related skill: [commons-card](../../skills/commons-card/SKILL.md)
- Tool pin: `1b7594e6263933e08ae196b4374373eb907c137f`, inspected 2026-10-05
- Upstream contracts: [ledger tools README](https://github.com/salmon-data-mobilization/salmon-knowledge-commons/blob/1b7594e6263933e08ae196b4374373eb907c137f/scripts/ledger/README.md), [CONTRIBUTING](https://github.com/salmon-data-mobilization/salmon-knowledge-commons/blob/1b7594e6263933e08ae196b4374373eb907c137f/CONTRIBUTING.md)

## Current role

`commons-card` is a read-only front door to three existing tools in an already
authorized private local checkout. It calls `okf-check.py` for card structure,
`ledger_table.py --dry-run` to print a candidate in-card ledger section,
and explicit `ledger_check.py --from-card` for the citation trail recorded in
the supplied card. It can also print the pinned contributor checklist.

The plugin ships no commons content and exposes no content acquisition,
source search, data API, model execution, card writing, compiler, or
publication route. Invoke the skill explicitly for this local workflow;
the existing selector's hardcoded package routes do not select it automatically.

## Current posture

- supported: metadata/schema structure checks
- partial: printing candidate ledger sections and commit-pinned structural provenance
- missing: discovery, entity resolution, crosswalks, scientific assessment, data access, bulk/API access, and publication

Synthetic offline controls exercise the wrapper and upstream structural
contracts. They establish no source evidence, scientific conclusion,
independent citation verification, human attestation, or scored model quality.

## Attribution and approval limits

The pinned ledger README records three outstanding attribution limits: a
later-overturned negative can still appear standing; shared filenames or
commits can associate a negative with a source it did not cover; and a row
that does not name its card can list another card's places. Keep these findings
visible rather than treating a generated table as a verified account.

`ledger_check.py --from-card` checks the recorded trail's structure. It cannot
determine whether a located passage supports the sentence. `citations_checked`
still awaits B-123's schema split; the documented `--checked-only` CI step has
no actual cards to check at this pin. An exit status of zero there is empty
coverage, not citation verification.

The skill neither writes `citations_checked` or `verified` nor promotes status,
mints terms, changes source access, or claims approval. The upstream
CONTRIBUTING checklist retains its human judgement gates. Printing that
checklist does not satisfy them.
