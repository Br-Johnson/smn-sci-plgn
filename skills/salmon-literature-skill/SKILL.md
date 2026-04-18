---
name: salmon-literature-skill
description: Search PubMed for salmon-related literature using NCBI E-utilities and return compact article summaries. Use when the user asks for papers, literature scans, or salmon-topic references.
---

## Operating rules

- Use `scripts/salmon_literature.py` for literature search.
- Keep first-pass searches compact with `retmax=5` or `retmax=10`.
- Prefer the smallest species or topic query that answers the question.
- Save raw payloads only when the user explicitly asks for machine-readable output.

## Input

- Read one JSON object from stdin.
- Required field: `query`
- Optional fields:
  - `species`
  - `retmax`
  - `mindate`
  - `maxdate`
  - `sort`
  - `save_raw`
  - `raw_output_path`
  - `timeout_sec`

Example:

```bash
echo '{"query":"climate change migration timing","species":"Chinook salmon","retmax":5}' | python skills/salmon-literature-skill/scripts/salmon_literature.py
```
