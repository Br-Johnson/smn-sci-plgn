---
name: salmon-research-framework-skill
description: 'Explains the local helper contract and scientific/privacy limitations without network or model calls inside the helper. Offline smoke case; live harness evaluation is opt-in.'
tags: [smoke]
max_turns: 10
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Use this skill to explain the actual local commands for inspecting a private research project and preparing an explicit research framework. Do not fetch data, create files, run models or publish. Explain why winter capture alone does not establish first-winter age and why an embargo expiry does not publish a project. Run the helper with --help to confirm its actual commands.
