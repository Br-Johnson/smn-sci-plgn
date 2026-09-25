---
name: metasalmon-skill
description: 'Reports the package engine''s runtime and the adapter''s actions without validating anything. A live run needs --allow-tools Bash and WebFetch(domain:...) grants for uv''s first install of metasalmonpy, pinned at v0.5.0: github.com, api.github.com, raw.githubusercontent.com, pypi.org, files.pythonhosted.org.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Check whether the Salmon Data Package engine is available in this environment and which package actions this plugin exposes. Don't validate any package; I just want the runtime report and the action list.
