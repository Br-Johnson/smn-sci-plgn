# Seed Normalization Schema

This is the current seed schema for the scaffold, plus the bounded Columbia Basin v0 identity hint slice.

## Species

Normalize to:

- common name
- scientific name
- salmon group

Current species set:

- Chinook salmon / *Oncorhynchus tshawytscha*
- Coho salmon / *Oncorhynchus kisutch*
- Sockeye salmon / *Oncorhynchus nerka*
- Chum salmon / *Oncorhynchus keta*
- Pink salmon / *Oncorhynchus gorbuscha*
- Masu salmon / *Oncorhynchus masou*
- Atlantic salmon / *Salmo salar*
- Steelhead / rainbow trout / *Oncorhynchus mykiss*

## Jurisdictions

Current seed jurisdictions:

- NOAA Fisheries
- Fisheries and Oceans Canada
- StreamNet
- PTAGIS
- CRITFC
- NPAFC
- PacFIN

## Management-unit systems

Current seed unit systems:

- `CU`
- `SMU`
- `DU`
- `ESU`
- `DPS`
- `HUC`
- `PIT`
- `CWT`

## Important limitation

This schema is a routing aid only.

It is not yet:

- a canonical salmon identity graph
- a population crosswalk registry
- a versioned ontology service

## Identity hints

The normalizer can also emit `identity_hints` when the input matches the bounded Columbia Basin v0 slice under `registry/identity/columbia-basin-v0.json`.

The response also includes an `identity_slice` summary with the slice ID, region, authority posture, and record count.

Each hint is non-authoritative and may include:

- `canonical_local_id`
- `label`
- `entity_type`
- `matched_text`
- `matched_field`
- `mapped_target_id`
- `mapping_relation`
- `confidence`
- `record_status`
- `valid_from`
- `valid_to`
- `valid_time_or_version`
- `provenance`
- `slice_id`

The hint slice is intentionally narrow and should be treated as a local routing cue, not basin-wide truth.
