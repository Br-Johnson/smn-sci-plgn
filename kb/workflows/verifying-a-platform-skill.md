# Verifying a Platform Skill

1. Run the narrow smoke calls for the skill.
2. Confirm the platform card still matches the skill surface and access model.
3. Confirm the platform card `access_tier` still matches the real access posture.
4. Confirm the wiki page still points to the right platform card and skill.
5. Confirm the related graph node and `uses_platform` or `constrained_by` edges still match reality.
6. Update the platform card `last_verified_date`.
7. If the verification changed parity meaning, update [docs/platform-gap-register.md](../../docs/platform-gap-register.md).
8. Append the verification event to [kb/log.md](../log.md).
9. Re-run `python3 scripts/validate_scaffold.py`.
