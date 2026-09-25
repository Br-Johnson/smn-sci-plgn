---
name: salmon-research-router-skill
description: 'Router plans a multi-source route without fetching. It needs no network, and the no-data-source grader fails any run that calls a source adapter.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Plan, don't fetch: I want to know how many spring Chinook returned to the upper Columbia River last year and how that compares with the long-term trend. Tell me which of your salmon skills you would use, in what order, and what each one needs (keys, tokens, nothing) before you run anything. Do not call any data source yet.
