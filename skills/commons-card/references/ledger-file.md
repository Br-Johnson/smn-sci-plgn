# The ledger file

`ledger_table` reads one or more citation-ledger JSON files and writes a
card's `## Citation ledger` section from them. This page describes the shape
that `scripts/ledger/ledger_table.py` reads at the pinned commons commit, in
this plugin's words. When the pin moves, check it against that script's
`Ledger` and `Fact` classes.

```json
{
  "producer": "who made this file, such as the session or agent",
  "date": "2026-10-15",
  "rows": [],
  "negatives": [],
  "terms": [],
  "card_plan": []
}
```

Only `rows` is required. A file can also be a bare list of rows. `producer`
and `date` stand in for a row's `checked_by` and `checked_at` when the row has
none.

## Rows: what one check found about one source

| Field | What it holds |
|---|---|
| `source_id` | The id of the card's `sources` entry the row is about. Required. `.` and `_` match `-`. |
| `citation`, `doi`, `url` | The source as cited. A DOI or URL also ties the row to a `sources` entry with the same `resource`. |
| `resolution_status` | `resolved`, `unresolved` or `mismatch`. A cited source with no `resolved` row fails `check_card`. |
| `resolution_method` | How the source was resolved, named plainly: `CrossRef`, `http-fetch, title_match=true`, `local checkout at <commit>`. The table's "Resolved by" label comes from it. |
| `retrieved_title` | The title the resolution returned. |
| `fulltext_obtained`, `fulltext_how` | `true` makes the table read `yes`. `false` reads `abstract only` when `fulltext_how` says abstract, and `record only` otherwise. |
| `passage_located` | Whether the passage was found. A row that says `true` must also say where, or the card fails `check_card`. |
| `passage_section_or_page` | Where the passage is: a page, section, line or field. Separate several places with ` \| `. The table shows the places that the card's footnote for the source also names, so name the same place in both. |
| `passage_paraphrase` | The passage in your own words. |
| `verbatim_short` | A short quote for each place, in the same order and separated the same way. The table shows a quote only where the card itself already quotes it. |
| `passages` | Instead of the two fields above, a list of `{"section_or_page": ..., "quote": ...}`. |
| `supports_claims` | Which of the card's claims the passage supports. |
| `checked_at`, `checked_by` | The date of the check and who made it. They make the table's "Checked on ... by ..." line. |
| `cards` | Optional: the card file names this row's places apply to, when one ledger serves several cards. |

A source that may only be paraphrased, because its licence was not established
or is non-commercial (CC BY-NC, for example), should say so in its row or in the
card's source entry. The table then shows no quote from it.

## Negatives: searches that found nothing

```json
{"query": "what was searched for", "where": "where it was searched", "result": "what came back"}
```

A negative is listed under the card it concerns, footnoted to the cited sources
it searched. The script decides which card from the `query`, so name the card's
file, or a source the card cites, in it. A negative that names neither is
reported as unassigned and appears in no card. It is also left out when the
card does not cite every source it names, or when those sources' rows do not
cover the places it searched; the report says which.

A row whose `resolution_status` is `unresolved` or `mismatch`, for a source the
card does not cite, appears under "Tried, not cited", footnoted to the cited
source that led to it.

## Terms and card plans

For a batch of cards about ontology terms, `terms` lists
`{"iri": ..., "label": ...}` and `card_plan` lists
`{"path": "concepts/<card>.md", "covers_terms": [<iri>, ...]}`. A negative that
names a term then goes to the cards that cover it. Without a `card_plan` entry,
a card covers the terms among its `alignment` exact and related IRIs.
