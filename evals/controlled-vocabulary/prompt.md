---
name: controlled-vocabulary
description: 'Build a fictional local SKOS vocabulary and an unexecuted W3ID/GitHub Pages publication proposal. Offline file workflow; no network, registration, deployment or paid model calls inside the helper.'
tags: [smoke, authoring]
max_turns: 15
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Create a fictional controlled-vocabulary demonstration locally with stable W3ID
term IRIs and a GitHub Pages publication proposal. Use the bundled --demo init
in cv-demo, validate it, prepare its immutable local release, build cv-preview,
and prepare publication files in cv-publication. Inspect the resulting manifest
and HTTP test plan. Do not contact any service, register a namespace, push a
repository or deploy anything. Explain the namespace collision-check result,
where machine representations live, and which real publication checks remain.
