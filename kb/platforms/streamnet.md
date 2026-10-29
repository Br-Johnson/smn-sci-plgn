# StreamNet

- Platform card: [registry/platforms/streamnet.json](../../registry/platforms/streamnet.json)
- Related skill: [streamnet-api-skill](../../skills/streamnet-api-skill/SKILL.md)

## Current role

StreamNet is the current scaffold's main structured source for Coordinated Assessment table metadata and records.

## Current posture

- supported: metadata/schema, abundance/assessment
- partial: discovery/search, provenance/versioning, bulk-access ergonomics
- missing: entity lookup, identifier crosswalks, telemetry, hatchery, harvest, genetics, package/export

## Why it matters

It is one of the strongest current structured assessment sources, but the plugin only exposes a narrow slice and still lacks an identity layer over the records.


## Plugin authentication boundary

Credentials are configured in the user's local environment, never supplied in
chat or JSON. Authenticated requests stay on the fixed HTTPS source origin;
cross-origin and downgrade redirects are refused. Ordinary output and saved
JSON redact credentials. See [local authentication](../../docs/source-authentication.md)
for the user-run setup and synthetic verification path.
