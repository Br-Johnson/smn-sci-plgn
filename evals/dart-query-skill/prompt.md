---
name: dart-query-skill
description: 'Lists the DART query pages the skill knows and picks the one for PIT-tag observations. The catalog is built into the script, so a live run needs --allow-tools Bash and no network.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Which Columbia River DART query pages does this plugin know about, and which one would I use for PIT-tag observations? List the page names with their DART paths.
