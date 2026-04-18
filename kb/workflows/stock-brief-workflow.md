# Stock Brief Workflow

Use this workflow when you need to verify or extend the salmon stock-brief composite scaffold.

## What this page covers

- How to check that the workflow still matches the current repo surface.
- How to extend the fixed output contract without weakening provenance.
- How to recognize scaffold-only gaps instead of pretending the workflow is complete.

## Verify

1. Read [salmon-stock-brief-workflow-skill](../../skills/salmon-stock-brief-workflow-skill/SKILL.md) and confirm the contract still matches the intended stock-brief shape.
2. From the repo root, render a sample skeleton with `python3 skills/salmon-stock-brief-workflow-skill/scripts/stock_brief_contract.py --template`.
3. From the repo root, validate a generated brief with `python3 skills/salmon-stock-brief-workflow-skill/scripts/stock_brief_contract.py path/to/brief.md`.
4. Confirm every factual claim has a provenance tag or an explicit inference label.
5. Confirm the workflow does not claim authoritative identity resolution.
6. Confirm the evidence order still reflects the sources the repo can actually reach.

## Extend

1. Keep the section order in the skill and helper script synchronized.
2. Add a new evidence subsection only if the repo has a real source lane for it.
3. Preserve the provenance fields and do not collapse primary evidence into summary prose.
4. If the target can be ambiguous, preserve that ambiguity in the brief rather than hiding it.
5. Add new failure modes when a new source surface can fail in a different way.
6. If the contract changes, update the helper script first so maintainers can validate the new shape.

## Scaffold boundaries

- This workflow is a composite scaffold, not an integration point.
- It should not be used to invent identity wrappers, downstream adapters, or routing-map entries.
- It should remain honest about partial coverage until the main agent wires it into the broader stack.
