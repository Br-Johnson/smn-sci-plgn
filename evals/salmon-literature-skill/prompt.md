---
name: salmon-literature-skill
description: 'Searches PubMed for three papers and reports their PubMed IDs. A live run needs --allow-tools Bash and a WebFetch(domain:eutils.ncbi.nlm.nih.gov) grant.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Find three recent PubMed papers on marine heatwave effects on sockeye salmon and give me titles with PubMed IDs.
