# Updating After Upstream Drift

Use this workflow when validation or manual checks show that an upstream version, auth model, or payload shape changed.

1. Confirm the drift against the upstream source, not just a cached local assumption.
2. Update the relevant platform card in `registry/platforms/`.
3. Update the related wiki page in `kb/platforms/`.
4. Update the related graph node or edge if the drift changes routing, pairing, or governance constraints.
5. Update the related skill if the live change affects behavior.
6. Update [docs/platform-gap-register.md](../../docs/platform-gap-register.md) if the drift changes parity risk.
7. Append the change to [kb/log.md](../log.md).
8. Re-run `python3 scripts/validate_scaffold.py`.
