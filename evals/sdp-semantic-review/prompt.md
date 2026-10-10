---
name: sdp-semantic-review
description: 'Asks how a Salmon Data Package''s semantic review packet gets judged here, and has the skill check that the package engine supports the packet, without building or judging anything. A live run needs --allow-tools Bash and WebFetch(domain:...) grants for uv''s first install of metasalmonpy, pinned at v0.6.0: github.com, api.github.com, raw.githubusercontent.com, pypi.org, files.pythonhosted.org. The judging itself is scored offline: replay_theme_a.py replays answer files through the package and scores them on the Theme A oracles in theme-a/.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
My Salmon Data Package still has ontology IRIs to choose, and I'd rather you judge its semantic review packet here than turn on the package's own LLM review. Before we start, check that the package engine in this environment can write and read review packets, then tell me the steps you'll take and what I'll still have to confirm myself. Don't build or judge anything yet.
