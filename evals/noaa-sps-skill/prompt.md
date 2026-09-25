---
name: noaa-sps-skill
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Pull the NOAA Salmon Population Summary home page and tell me what the site is for and whether it exposes a JSON API I could script against.
