---
name: metasalmon-skill
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Check whether the Salmon Data Package engine is available in this environment and which package actions this plugin exposes. Don't validate any package; I just want the runtime report and the action list.
