---
name: salmon-stock-brief-workflow-skill
description: Scaffolded composite workflow for producing structured salmon stock briefs from normalized candidates and downstream source evidence. Use when the user needs a repeatable brief contract with explicit provenance and caveats, but do not assume authoritative identity resolution or full wrapper coverage.
---

# Salmon Stock Brief Workflow

## Scope

This is a scaffold for a future composite workflow. It is not wired into router maps, and it does not own identity resolution or source wrappers.

Use it when a stock brief needs to be assembled from a normalized target plus downstream evidence.

## Operating rules

- Start from the smallest plausible stock candidate set.
- Do not claim authoritative identity resolution.
- Keep ambiguity visible when the target is uncertain.
- Prefer primary evidence over summaries when they disagree.
- If a source lane is unavailable, skip it and say so.
- Separate sourced facts from inference.
- Preserve provenance for every factual claim.

## Recommended evidence order

Keep the evidence section in this order:

1. Assessment and status.
2. Telemetry, passage, and movement.
3. Hatchery, harvest, and management.
4. Habitat, ocean, and climate context.
5. Literature and report context.
6. Contradictions and unresolved items.

## Fixed output contract

Return markdown with these sections in this order:

1. `Request`
2. `Brief target`
3. `Bottom line`
4. `Evidence`
5. `Provenance`
6. `Caveats and failure modes`
7. `Open questions`

The `Evidence` section must keep the recommended evidence order above.

## Provenance expectations

- Every factual claim needs a source tag or an explicit `inference` label.
- Record source name, retrieval date, and source type when available.
- Distinguish primary evidence from secondary summaries and workflow inference.
- If evidence is missing, write `not found` rather than filling the gap.

## Known failure modes

- Multiple stocks share the same plain-language label.
- Normalization returns a plausible candidate, not a canonical identity.
- One source lane is missing, rate-limited, or stale.
- Sources disagree on time window, geography, or stock boundary.
- A user asks for a management unit, hatchery group, or aggregate and the workflow treats it as a stock.
- Briefs overstate certainty when only partial evidence exists.

## Helper script

Use `scripts/stock_brief_contract.py` to render the template or validate that a generated brief still contains the required sections.
