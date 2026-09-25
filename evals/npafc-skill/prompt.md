---
name: npafc-skill
description: 'Searches the NPAFC CKAN catalogue for salmon catch-statistics datasets. A live run needs --allow-tools Bash and a WebFetch(domain:data.npafc.org) grant.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Search the NPAFC catalogue for salmon catch statistics datasets and list the top few results with their dataset names.
