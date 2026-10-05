---
name: commons-card
description: Check an explicitly supplied commons card bundle, preview an in-card citation ledger, or check a card's existing ledger using a private pinned salmon-knowledge-commons checkout. Use for structural commons-card checks and the contribution checklist; it neither retrieves sources nor verifies claims.
---

# commons-card

This M21 first slice runs the existing commons tools. All card, schema and
ledger logic stays in salmon-knowledge-commons. It requires an already
available, trusted private checkout at commit
`1b7594e6263933e08ae196b4374373eb907c137f`; it does not fetch the checkout,
sources or real cards. Keep private output private.

## Run it

Supply the checkout and a separate caller workspace explicitly. The workspace
is the bundle to inspect, not the commons checkout. Validation reads every
eligible Markdown file below that workspace. Preview and check take explicit
card paths; preview also requires explicit ledger JSON paths. Relative input
paths are relative to the workspace. Parent traversal, symlinks, paths outside
the workspace and any overlap with the commons checkout are refused.

```bash
python3 -B "${CLAUDE_SKILL_DIR}/scripts/commons_card.py" validate --commons-checkout "$COMMONS_CHECKOUT" --workspace "$CALLER_BUNDLE"
python3 -B "${CLAUDE_SKILL_DIR}/scripts/commons_card.py" preview --commons-checkout "$COMMONS_CHECKOUT" --workspace "$CALLER_BUNDLE" --card concepts/synthetic-card.md --ledger synthetic-ledger.json
python3 -B "${CLAUDE_SKILL_DIR}/scripts/commons_card.py" check --commons-checkout "$COMMONS_CHECKOUT" --workspace "$CALLER_BUNDLE" --card concepts/synthetic-card.md
python3 -B "${CLAUDE_SKILL_DIR}/scripts/commons_card.py" checklist --commons-checkout "$COMMONS_CHECKOUT"
```

`${CLAUDE_SKILL_DIR}` identifies this skill directory in Claude Code; other
harnesses use `skills/commons-card` in the plugin checkout. `COMMONS_CHECKOUT`
and `CALLER_BUNDLE` above are explicit caller-supplied paths. The examples
name synthetic inputs; acceptance controls use fabricated cards and ledgers
only, without live sources or scientific data.

The upstream Python runtime needs preinstalled PyYAML, jsonschema and its
referencing/jsonschema-specifications dependencies. The helper installs
nothing. If a checkout or dependency is unavailable, report the failure;
do not retrieve private contents or start a package installation implicitly.

## Outputs and boundaries

The helper emits one JSON envelope with `action`, required `pin`,
`output_kind`, `structural_only`, `returncode`, and the completed upstream
process's `stdout` and `stderr` strings. It returns the upstream exit code.
Pin/path/process refusals return 2 and an `error` instead of completed streams;
invalid CLI usage follows argparse's normal usage error. Report upstream
findings honestly, including warnings and runtime failures.

- `validate` runs `okf-check.py --json` against the whole explicit caller
  bundle and the pinned commons schema. `validation_findings` describes
  structural findings, not verified knowledge.
- `preview` forces `ledger_table.py --dry-run`, with no `--report` or writable
  mode. `ledger_preview` is a generated section. Successful generation can
  still contain unresolved or mismatched rows and failing passages. It is
  never a validation pass. The existing generator's checked-on line describes
  the supplied ledger's records; it does not mean this helper checked sources.
- `check` forces `ledger_check.py --from-card` on every explicit card and
  returns `ledger_structure`. It never uses `--checked-only`. A structural
  pass does not establish whether a located passage supports the claim.
- `checklist` returns a short checklist attributed to pinned
  `CONTRIBUTING.md`, without checking or editing a card.

The helper verifies exact Git HEAD and six pinned execution/governance file
hashes before use, including the neighboring `ledger_table.py` imported by
`ledger_check.py`. Upstream Python runs with `-I -B`. This is trusted-host tool
integrity and read-only transport, not filesystem isolation, authentication,
reader permission or custody. Output may contain caller text and paths; keep
the complete envelope inside the caller's private workflow. It is not a
commons distribution artifact.

## Existing upstream limits

Preserve these limitations from pinned `scripts/ledger/README.md`:

- A negative overturned later cannot yet be marked superseded and can remain
  listed as standing.
- Shared filename/commit association can attribute a negative to a source its
  search did not cover.
- A row that names no card can place one card's locations in another's table.

At this pin, `citations_checked` awaits B123's schema split. The closed schema
does not admit it. Upstream CI's `--checked-only` step therefore has no cards
to check and can exit zero with “nothing to check.” This skill's explicit
card check avoids that skip; it does not supply the missing verification
scheme. Never add `citations_checked`, `verified`, trust-tier assertions or
human attestations as part of this slice. Do not mint ontology terms, promote
cards to stable, write real cards, publish contents or merge a plugin PR.

Pinned governance sources: `CONTRIBUTING.md` lines 8-46 and 48-102;
`scripts/ledger/README.md` lines 3-21 and 34-43;
`VERIFICATION.md` lines 8-23. No Tern scientific or human-attestation gate is
cleared by a commons structural finding.

## Offline evidence

`tests/test_commons_card.py` tests transport with fabricated checkout bytes and
mocked processes; it does not execute the private upstream tools.
The eval case uses a deliberately missing synthetic checkout and deterministic
graders to check honest refusal. Offline grader feasibility does not run a
model, score an eval or establish live scientific acceptance. Separately gated
integration controls run fabricated inputs through the actual pinned upstream
checkout when it is explicitly supplied.
