# metasalmon Skill Capabilities

Current supported actions:
- `runtime`
- `catalog`
- `sources_for_role`
- `find_terms`
- `fetch_salmon_ontology`
- `validate_salmon_datapackage`

Current intentional limits:
- no direct `create_sdp()` bridge from generic chat payloads yet
- no direct issue-submission or publication submission flow yet
- no local package installation step; the skill checks runtime and reports what is missing

Why this skill exists:
- `metasalmon` already implements important package-first semantic workflows
- this plugin should expose that engine, not fork it
