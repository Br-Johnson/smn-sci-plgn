---
name: psc-vocabulary
description: Inspect the local PSC discovery runtime without reading any source or calling a network.
tags: [smoke, offline]
max_turns: 8
timeout_seconds: 120
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Inspect the PSC vocabulary discovery reader's runtime contract. Do not read any vocabulary source or call a network. Tell me its supported local source schema and whether it writes files or fetches sources.
