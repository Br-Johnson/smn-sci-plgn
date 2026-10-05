---
name: commons-card
description: 'Offline fail-closed smoke with synthetic fixture paths and a deliberately missing checkout. No private commons cards, source retrieval, network or paid judge are needed; all graders are deterministic. A live model eval is not part of offline acceptance.'
tags: [smoke]
max_turns: 8
timeout_seconds: 120
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Use commons-card to attempt a structural validation of the supplied synthetic
bundle at `evals/commons-card/fixtures/bundle`. Use the helper
`commons_card.py` with the explicit checkout path
`evals/commons-card/fixtures/missing-checkout`, which is deliberately absent.
Run from this plugin checkout. Do not create or fetch that checkout, retrieve
sources, install dependencies, write cards or add verification entries.
Report the refusal and required pin. State clearly that no structural
validation completed and no claim was verified. Do not run a live model eval.
