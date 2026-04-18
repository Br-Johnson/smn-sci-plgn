# Platform Gap Method

This repo tracks platform capability gaps in two layers.

## Layer 1: parity rollup

[docs/platform-gap-register.md](../../docs/platform-gap-register.md) records the cross-platform blockers that matter for parity with the Life Science Research plugin.

## Layer 2: platform cards

[registry/platforms/](../../registry/platforms/) records source-specific truth:

- access model
- capability status by category
- blockers
- governance constraints
- evidence links
- drift/watch fields

## Status vocabulary

Platform capability status is normalized to:

- `supported`
- `partial`
- `missing`
- `gated`
- `unknown`

## Capability categories

The platform cards use the categories in [registry/vocab.json](../../registry/vocab.json).

These categories let different sources be compared without forcing them into identical products.

Related:
- [Governance-aware access gap](../gaps/governance-access-gap.md)
- [Adding a new platform](../workflows/adding-a-new-platform.md)
- [Updating after upstream drift](../workflows/updating-after-upstream-drift.md)
