# Adding a New Platform

1. Read the platform docs and confirm the real access model.
2. Add or update the skill if the repo should query the source.
3. Add a platform card under `registry/platforms/`.
4. Set the platform card `access_tier` and keep the prose `auth_access_model` aligned with it.
5. Add a wiki page under `kb/platforms/`.
6. Add or update the skill-to-platform entry in `registry/skill-platform-map.json`.
7. Add or update the related node and `uses_platform` edges in `registry/skill-graph.json`.
8. Update router references and selector fixtures if the new source changes lane coverage.
9. Update [docs/platform-gap-register.md](../../docs/platform-gap-register.md) if parity meaning changes.
10. Append a log entry in [kb/log.md](../log.md).
11. Run `python3 scripts/validate_scaffold.py`.
12. Run `python3 -m unittest discover -s tests -p 'test_*.py'`.
