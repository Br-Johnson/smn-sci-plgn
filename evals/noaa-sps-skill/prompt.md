---
name: noaa-sps-skill
description: 'Fetches the NOAA SPS home page and asks whether SPS offers a JSON API. A live run needs --allow-tools Bash and a WebFetch(domain:www.webapps.nwfsc.noaa.gov) grant. The skill''s home URL returned 404 on 2026-09-25.'
tags: [smoke]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---
Pull the NOAA Salmon Population Summary home page and tell me what the site is for and whether it exposes a JSON API I could script against.
