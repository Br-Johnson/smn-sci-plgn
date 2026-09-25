# Verifying a Platform Skill

1. Run the narrow smoke calls for the skill (`uv run` for the package adapters).
2. Run its eval case: `claude plugin eval . --case <skill> --allow-tools Bash --ablation none`.
3. Confirm the platform card still matches the skill surface and access model.
4. Confirm the platform card `access_tier` still matches the real access posture.
5. Confirm the wiki page still points to the right platform card and skill.
6. Confirm the related graph node and `uses_platform` or `constrained_by` edges still match reality.
7. Update the platform card `last_verified_date`.
8. If the verification changed parity meaning, update [docs/platform-gap-register.md](../../docs/platform-gap-register.md).
9. Append the verification event to [kb/log.md](../log.md).
10. Re-run `python3 scripts/validate_scaffold.py`; it also enforces the [thin front door](../concepts/thin-front-door.md) contract.
