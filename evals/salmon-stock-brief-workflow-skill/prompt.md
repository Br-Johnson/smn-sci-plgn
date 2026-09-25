---
name: salmon-stock-brief-workflow-skill
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write]
---
Write a stock brief skeleton for Upper Columbia spring Chinook into a file called brief.md using your structured brief contract. Don't fetch any evidence; fill every evidence subsection with "not found" and keep the required sections in order. Then validate the file with the contract helper.
