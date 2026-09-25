# Updating After Upstream Drift

Use this workflow when validation or manual checks show that an upstream version, auth model, or payload shape changed.

1. Confirm the drift against the upstream source, not just a cached local assumption.
2. Update the relevant platform card in `registry/platforms/`. For a package release, bump `pinned_releases` on the `metasalmon` card and the matching pin in every adapter script (`salmon_terms.py`, `metasalmon_api.py`) in the same change; the validator refuses a mismatch.
3. Update `access_tier` if the real access posture changed.
4. Update the related wiki page in `kb/platforms/`.
5. Update the related graph node or edge if the drift changes routing, pairing, or governance constraints.
6. Update selector fixtures if the drift changes which route should now be chosen.
7. Update the related skill if the live change affects behavior.
8. Update [docs/platform-gap-register.md](../../docs/platform-gap-register.md) if the drift changes parity risk.
9. Append the change to [kb/log.md](../log.md).
10. Re-run `python3 scripts/validate_scaffold.py`.
