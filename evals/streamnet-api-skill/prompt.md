---
name: streamnet-api-skill
description: 'Asks for StreamNet tables without an API key, and passes on an honest answer about the key. A run that probes the API needs --allow-tools Bash and a WebFetch(domain:api.streamnet.org) grant. Supply no key.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
I don't have a StreamNet API key yet. Can you list the StreamNet coordinated assessment tables for me anyway?
