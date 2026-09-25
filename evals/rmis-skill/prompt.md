---
name: rmis-skill
description: 'Reads the public RMIS version announcement, which needs no credentials. A live run needs --allow-tools Bash and a WebFetch(domain:www.rmis.org) grant.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
What is the current RMIS database version and its effective date according to the public RMIS announcement page? No credentials needed for this one.
