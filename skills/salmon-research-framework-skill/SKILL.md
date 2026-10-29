---
name: salmon-research-framework-skill
description: Draft and check a source-backed salmon research framework across life phases, outcomes, exposures and scales. Use to organise hypotheses and evidence requirements; it does not fit models or estimate survival.
---

# Research framework proposals

Use a framework to state what would be tested and what evidence could support
the test. Separate direct survival estimates, encounter composition, indices and
environmental proxies. A valid file is a proposal awaiting scientific review.

Create a draft from a private workbench export, then edit the explicit fields:

```sh
python3 scripts/research_framework.py framework-template --bundle project.json
python3 scripts/research_framework.py framework-check --framework framework.json
```

Run from this skill directory or use the script's actual installed path. Claude
Code supplies `${CLAUDE_SKILL_DIR}`; Codex can use the checkout/installed skill
path. Both wrappers share the same offline implementation. Output goes to
stdout; save it only to a user-authorized local draft path.

The template records question, species, unit, life phase, cohort and age evidence,
outcome/evidence type, exposures, spatial/temporal scale, alternatives, sources
and limitations. Keep unknown fields explicit. Do not infer:

- first-winter status from a winter date, life-stage label, length or weight;
- assignment probabilities from GSI hard calls;
- direct survival from catch counts, recruitment/spawner ratios or condition;
- biological identity from matching labels, proximity or equal numbers;
- historical migration tracks from one winter's encounter locations.

Selecting `first_winter` requires explicit `marineAgeEvidence` and
`cohortEvidence`; selecting `direct_survival` requires `survivalEvidence`.
These checks require evidence entries, not their scientific acceptance. Preserve
source definitions, age conventions and detection/effort limitations for review.
If the source only supports winter encounters of unknown marine age, use
`winter_mixed` and `encounter`. Missing information is a useful readiness result.

For source retrieval use the existing source skills; use `salmon-terms` for
declared vocabulary candidates. No new ontology term, crosswalk acceptance,
model result, survival estimate or publication permission follows from this
workflow. Keep private evidence private; prepare a separate disclosure-reviewed
contribution with `salmon-workbench-skill` when appropriate.

Read [the scientific framing](references/framing.md) when explaining the
relationship to the Likely Suspects Framework and BECI.
