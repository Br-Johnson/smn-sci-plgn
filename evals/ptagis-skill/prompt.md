---
name: ptagis-skill
description: 'Asks which PTAGIS calls need a bearer token. The skill''s own docs answer it, and a run that also probes the API needs --allow-tools Bash and a WebFetch(domain:api.ptagis.org) grant. Supply no token.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Which PTAGIS data can this plugin reach without a bearer token, and which calls need one? I'm deciding whether to request PTAGIS access for a PIT-tag passage question.
