---
name: critfc-crosswalk-skill
description: 'Fetches the CRITFC ArcGIS REST root through the skill and reports what it lists. A live run needs --allow-tools Bash and a WebFetch(domain:gis.critfc.org) grant. That host did not resolve on 2026-09-25, so a passing run currently reports the fetch error honestly.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Fetch the CRITFC crosswalk ArcGIS REST root and tell me what services or folders it lists. I want to know if it can help reconcile Columbia Basin population names.
