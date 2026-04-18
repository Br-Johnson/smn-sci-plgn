# Adding a New Platform

1. Read the platform docs and confirm the real access model.
2. Add or update the skill if the repo should query the source.
3. Add a platform card under `registry/platforms/`.
4. Add a wiki page under `kb/platforms/`.
5. Add or update the skill-to-platform entry in `registry/skill-platform-map.json`.
6. Add or update the related node and `uses_platform` edges in `registry/skill-graph.json`.
7. Update router references if the new source changes lane coverage.
8. Update [docs/platform-gap-register.md](../../docs/platform-gap-register.md) if parity meaning changes.
9. Append a log entry in [kb/log.md](../log.md).
10. Run `python3 scripts/validate_scaffold.py`.
