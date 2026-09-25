---
name: salmon-terms
description: 'Term lookup goes through metasalmonpy via uv, never a local JSON-LD read. A live run needs --allow-tools Bash and WebFetch(domain:...) grants for uv''s first install (github.com, api.github.com, raw.githubusercontent.com, pypi.org, files.pythonhosted.org) and for the smn index (w3id.org).'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
What is the shared salmon ontology term and IRI for escapement? Only search the shared smn source, and tell me the definition it carries.
