---
name: commons-card
description: Write or check a concept card for the salmon knowledge commons, with its in-card citation-ledger table, by running the commons' own validator and ledger tools at a pinned commons commit against the user's clone. Use when the user adds or edits a commons card, has citation-ledger JSON to turn into a card's ledger table, wants the card-only ledger check or the bundle validation, or is getting a commons pull request ready.
---

# commons-card

The [salmon knowledge commons](https://github.com/salmon-data-mobilization/salmon-knowledge-commons)
holds source-backed concept cards about salmon. It is private: only its members
can read it. Its rules and its checks live in the commons itself, and this
skill runs them at one pinned commons commit, against the user's own clone, and
returns what they print:

| Action | Runs, at the pin | For |
|---|---|---|
| `validate` | `scripts/okf-check.py` | the whole bundle against the commons' closed schema and rules |
| `ledger_table` | `scripts/ledger/ledger_table.py` | writing a card's `## Citation ledger` section from ledger JSON |
| `check_card` | `scripts/ledger/ledger_check.py --from-card` | holding every cited source to one resolved table row with a located passage |
| `checklist` | `CONTRIBUTING.md` | the commons' rules for a contribution and for what an agent may merge |

The skill decides nothing about a card and ships no commons content. Each call
copies the pinned files out of the clone's own git history into a temporary
directory, runs them there, and deletes them.

## Run it

It needs git, [uv](https://docs.astral.sh/uv/), and a clone of the commons that
contains the pinned commit. The adapter's script block declares PyYAML and
jsonschema, which the commons' scripts import, and uv installs both on first
use. Where uv's cache directory isn't writable, as in some sandboxed runs, set
`UV_CACHE_DIR` to a writable directory first.

```bash
echo '{"action":"runtime","commons_dir":"path/to/salmon-knowledge-commons"}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/commons_card.py"
echo '{"action":"ledger_table","cards":["concepts/<card>.md"],"ledgers":["/abs/path/ledger.json"]}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/commons_card.py"
echo '{"action":"check_card","cards":["concepts/<card>.md"]}' | uv run -q "${CLAUDE_SKILL_DIR}/scripts/commons_card.py"
```

`${CLAUDE_SKILL_DIR}` is this skill's directory. Claude Code fills it in; in any
other harness use the folder that holds this file, which is
`skills/commons-card` in a checkout of the plugin.

The clone is `commons_dir` when the request names one, else the
`SALMON_COMMONS_DIR` environment variable, else the directory the adapter runs
in. If the user has no clone, or no access to the commons, say so and stop:
the skill has no other way to reach it.

## Actions

The adapter reads one JSON object from stdin and writes one to stdout.

- `runtime` (the default): the pin, the clone and how it was found, and whether
  PyYAML and jsonschema are importable.
- `validate`: the validator's findings under `output`: `concepts`, `gaps`,
  `errors` and `warnings`. With `gaps: true`, `output` is the gap register.
- `ledger_table`: `cards` and `ledgers` are required. Without `write: true` it is
  a dry run: `stdout` holds the sections it would write and no card changes.
  `report` holds what the script found, including the negatives and tried rows
  it left out of a card and why. With `write: true` it writes the sections into
  the cards.
- `check_card`: `cards` is required. `stdout` has a line per card, `ok` or
  `FAIL`, with its errors and warnings under it. `checked_only: true` keeps only
  the cards whose frontmatter carries a `citations_checked` entry, which is the
  selection the commons' CI checks.
- `checklist`: the text of `CONTRIBUTING.md` at the pin, and
  `differs_in_checkout` when the clone's copy is different.

Card paths are relative to the clone's root, as the commons' own commands take
them. A ledger path is absolute or relative to the clone's root. Every response
carries `pin` and `checkout`: the clone's path, its `head`, `contains_pin`
(whether HEAD descends from the pin), and `drift`, the files the adapter runs or
prints whose copy in the clone differs from the pinned one. Every action that
runs a script also carries `ran` (the script, the pin and the arguments),
`exit_code` and `stderr`; a non-zero exit gives `ok: false`.

The pin was reviewed on 2026-10-29. If any pinned tool, schema or contribution
rule differs in the checkout, `validate`, `check_card` and `ledger_table`
return `ok: false` with `error.code: upstream_drift` before running a script.
This also blocks ledger writes. `runtime` and `checklist` remain available to
inspect the pin and the differences; their success is not a validation pass.
There is no implicit mode that runs historical checks against changed rules.

## Writing or changing a card

1. Run `runtime`. If it is not ok, its message says what to fix, and if a
   dependency reads false, run the adapter with uv as shown above. If `drift`
   is not empty, the commons has changed those files since this plugin's pin:
   stop before writing or checking cards and report the differences. Update
   the plugin to a reviewed compatible pin; do not change the clone's rules
   to make a historical checker pass. The commons' own CI remains the
   contribution authority.
2. Run `checklist` and read it before writing anything. It is the commons' own
   statement of what a card must carry and of what an agent may and may not do
   there. If `differs_in_checkout` is true, read the clone's copy as well and
   follow it.
3. Build the citation ledger before you write the claims it supports: for each
   source, resolve it, read it, locate the passage that supports each claim and
   record where that passage is, and record every search that found nothing.
   [references/ledger-file.md](references/ledger-file.md) is the file format.
   To find candidate sources, `salmon-literature-skill` searches PubMed; each
   source it finds still needs its own row.
4. Write the card in the clone, following the commons' own `AGENTS.md` and
   schema. Every claim carries a footnote whose id names an entry in the
   card's `sources`, and that id is the `source_id` of its ledger rows.
5. Run `ledger_table` as a dry run and read both the sections and the report.
   Where the report leaves a negative or a tried row out, fix the ledger so the
   row names the card, term or source it concerns. Then run it with
   `write: true`.
6. Run `check_card` on every card you wrote or changed. Fix what it reports in
   the ledger or the card and write the section again; never edit the
   generated section by hand.
7. Run `validate`. Zero errors is the bar.
8. Report what you established and what you could not. Opening the pull
   request is the user's call; the checklist says what it needs, and the
   commons' CI runs its own checks on it.

## Rules

- A successful `check_card` means every citation has a checked trail, not that
  every claim is right: no check here can tell whether the located passage says
  what the card's sentence says. A successful `validate` checks the bundle's
  schema and rules; it does not replace `check_card` or the commons' other CI
  checks. Say which check passed when you report it.
- Writing a card or its ledger is not verifying it. Never record yourself as a
  card's verifier, and never describe your ledger as a human check.
- A ledger negative records a search that came back empty. It describes the
  search, not the world, so never report one as evidence that something is
  absent.
- Keep the ledger JSON outside the clone. It is a working file; the card's
  table is the record.
- Copy no commons text into anything public, this plugin included.

## Not covered

- Finding, reading and judging sources is your work; the ledger records it.
- The commons' other CI checks, such as the verification diff against the base
  branch and the compiler, run on the pull request, not here.
- The skill opens, reviews and merges no pull request.
