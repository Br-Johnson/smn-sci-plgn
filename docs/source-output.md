# Source retrieval output

PTAGIS, RMIS data actions and NPAFC return a redacted preview by default. Each
collection contains at most five rows, and the **actual serialized stdout,
including JSON indentation and newline, is at most 16,384 UTF-8 bytes**. Long
strings, wide objects and deeply nested values can also be shortened; a tight
byte budget can reduce the row count further. Source summaries retain useful
metadata without repeating the same sample in `summary` and `records`.

`output` describes what happened:

- `mode`: `preview`, or `raw` after explicit opt-in.
- `record_count`: rows available in this returned response, before previewing.
  Lists use their length; known `records`, `results` and `resources` envelopes
  use that collection's length. Another nonempty metadata object counts as one.
- `preview_count`: rows represented in `records` after previewing.
- `truncated`: any output fields or records were shortened or omitted.
- `max_rows`, `max_bytes`: preview limits; `null` for explicit raw mode.

Source-reported totals and pagination remain in `summary` or the response
envelope. They can exceed `record_count`; a preview is not evidence that all
remote pages were retrieved. `source`, `action`, `url` and available retrieval
metadata identify the source. Oversized metadata may itself be shortened and
is covered by the truncation flag. Small metadata actions keep their useful
fields, including NPAFC resource details and RMIS announcements.

## Save locally

Use `save_raw: true` with an optional `raw_output_path`. Existing default file
names remain `ptagis-raw.json`, `rmis-raw.json` and `npafc-raw.txt`. A path alone
does not request saving. Saved data uses the existing credential redaction;
NPAFC JSON retains its response envelope and non-JSON text remains text.

Saving never implicitly enables bulk stdout. If the write fails, the result
has `ok: false`, `retrieval_ok: true`, `error.code: raw_output_failed` and a null
`raw_output_path`. The compact findings, count and source provenance remain so
the user can choose a writable file path without losing the retrieval result.

## Explicit raw stdout

Only JSON boolean `raw_stdout: true` returns the full redacted `records`
payload. Other values, including the string `"true"`, retain preview mode.
Use raw stdout only when the user explicitly requests bulk records in the
transcript. It deliberately removes preview byte/row bounds. `save_raw` and
`raw_stdout` are independent controls; local saving is the normal bulk route.
