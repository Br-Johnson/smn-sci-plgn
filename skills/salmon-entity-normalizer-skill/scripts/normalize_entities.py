from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, load_input, result_error


COLUMBIA_BASIN_SLICE_PATH = ROOT / "registry" / "identity" / "columbia-basin-v0.json"
LEGACY_IDENTITY_PATH = ROOT / "registry" / "identity" / "seed-crosswalks.json"

SPECIES = [
    {
        "canonical_name": "Chinook salmon",
        "scientific_name": "Oncorhynchus tshawytscha",
        "group": "Pacific salmon",
        "aliases": ["chinook", "king salmon", "spring chinook", "fall chinook", "o. tshawytscha"],
    },
    {
        "canonical_name": "Coho salmon",
        "scientific_name": "Oncorhynchus kisutch",
        "group": "Pacific salmon",
        "aliases": ["coho", "silver salmon", "o. kisutch"],
    },
    {
        "canonical_name": "Sockeye salmon",
        "scientific_name": "Oncorhynchus nerka",
        "group": "Pacific salmon",
        "aliases": ["sockeye", "red salmon", "kokanee", "o. nerka"],
    },
    {
        "canonical_name": "Chum salmon",
        "scientific_name": "Oncorhynchus keta",
        "group": "Pacific salmon",
        "aliases": ["chum", "dog salmon", "keta", "o. keta"],
    },
    {
        "canonical_name": "Pink salmon",
        "scientific_name": "Oncorhynchus gorbuscha",
        "group": "Pacific salmon",
        "aliases": ["pink salmon", "humpy", "o. gorbuscha"],
    },
    {
        "canonical_name": "Masu salmon",
        "scientific_name": "Oncorhynchus masou",
        "group": "Pacific salmon",
        "aliases": ["masu", "yamame", "o. masou"],
    },
    {
        "canonical_name": "Atlantic salmon",
        "scientific_name": "Salmo salar",
        "group": "Atlantic salmon",
        "aliases": ["atlantic salmon", "salmo salar"],
    },
    {
        "canonical_name": "Steelhead / rainbow trout",
        "scientific_name": "Oncorhynchus mykiss",
        "group": "salmonid",
        "aliases": ["steelhead", "rainbow trout", "o. mykiss"],
    },
]

JURISDICTIONS = {
    "noaa": "NOAA Fisheries",
    "noaa fisheries": "NOAA Fisheries",
    "dfo": "Fisheries and Oceans Canada",
    "fisheries and oceans canada": "Fisheries and Oceans Canada",
    "streamnet": "StreamNet",
    "ptagis": "PTAGIS",
    "critfc": "CRITFC",
    "npafc": "NPAFC",
    "pacfin": "PacFIN",
}

UNIT_PATTERNS = [
    (r"\bconservation units?\b|\bcus?\b", "Conservation Unit", "CU"),
    (r"\bstock management units?\b|\bsmus?\b", "Stock Management Unit", "SMU"),
    (r"\bdesignatable units?\b|\bdus?\b", "Designatable Unit", "DU"),
    (r"\bevolutionarily significant units?\b|\besus?\b", "Evolutionarily Significant Unit", "ESU"),
    (r"\bdistinct population segments?\b|\bdpss?\b|\bdps\b", "Distinct Population Segment", "DPS"),
    (r"\bhuc[-\s]?\d+\b", "Hydrologic Unit Code", "HUC"),
    (r"\bpit\b|\bpit[-\s]?tag\b", "Passive Integrated Transponder", "PIT"),
    (r"\bcwt\b|\bcoded[-\s]?wire tag\b", "Coded Wire Tag", "CWT"),
]

ID_PATTERNS = [
    (r"\bHUC[-\s]?\d{4,12}\b", "HUC"),
    (r"\bCUs?\b", "CU"),
    (r"\bSMUs?\b", "SMU"),
    (r"\bDUs?\b", "DU"),
    (r"\bESUs?\b", "ESU"),
    (r"\bDPSs?\b", "DPS"),
    (r"\bPIT\b", "PIT"),
    (r"\bCWT\b", "CWT"),
]


def dedupe(items: list[dict], key: str) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        value = item[key]
        if value in seen:
            continue
        seen.add(value)
        result.append(item)
    return result


def normalize_for_match(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load_identity_slice() -> tuple[dict | None, list[dict], list[str]]:
    warnings: list[str] = []
    for path in (COLUMBIA_BASIN_SLICE_PATH, LEGACY_IDENTITY_PATH):
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"could not read {path.name}: {exc}")
            continue

        if isinstance(raw, dict) and isinstance(raw.get("records"), list):
            records = [record for record in raw["records"] if isinstance(record, dict)]
            return raw, records, warnings

        if isinstance(raw, list):
            records = [record for record in raw if isinstance(record, dict)]
            return (
                {
                    "slice_id": "legacy-seed-crosswalks",
                    "version": "compatibility",
                    "generated_on": None,
                    "scope": {
                        "region": "Columbia Basin",
                        "status": "bounded fallback",
                        "authority": "non-authoritative",
                        "assumption": "Legacy compatibility view loaded because the bounded slice file was unavailable.",
                    },
                    "scheme_definitions": [],
                    "records": records,
                },
                records,
                warnings,
            )

        warnings.append(f"{path.name} did not contain a recognized identity slice")

    return None, [], warnings


def iter_record_terms(record: dict) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for field in ("canonical_local_id", "label", "identifier_value", "mapped_target_id"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            candidates.append((field, value.strip()))

    aliases = record.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                candidates.append(("alias", alias.strip()))

    return candidates


def match_identity_record(record: dict, haystack: str) -> dict | None:
    for field, candidate in iter_record_terms(record):
        if normalize_for_match(candidate) in haystack:
            return {
                "canonical_local_id": record.get("canonical_local_id", ""),
                "label": record.get("label", record.get("canonical_local_id", "")),
                "entity_type": record.get("entity_type", ""),
                "matched_text": candidate,
                "matched_field": field,
                "mapped_target_id": record.get("mapped_target_id", ""),
                "mapping_relation": record.get("mapping_relation", ""),
                "confidence": record.get("confidence", ""),
                "record_status": record.get("record_status", ""),
                "valid_from": record.get("valid_from"),
                "valid_to": record.get("valid_to"),
                "valid_time_or_version": record.get("valid_time_or_version", ""),
                "provenance": record.get("provenance", []),
                "slice_id": record.get("slice_id", "columbia-basin-v0"),
                "bounded": True,
            }
    return None


def collect_text(payload: dict) -> str:
    text_parts = [
        str(payload.get("text", "")),
        str(payload.get("species", "")),
        str(payload.get("jurisdiction", "")),
    ]

    entity_ids = payload.get("entity_ids", [])
    if isinstance(entity_ids, list):
        text_parts.extend(str(value) for value in entity_ids if value is not None)
    elif entity_ids:
        text_parts.append(str(entity_ids))

    return " ".join(part for part in text_parts if part).strip()


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:
        emit(result_error("invalid_input", str(exc)))
        return

    if isinstance(payload, str):
        payload = {"text": payload}
    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object or string"))
        return

    text = collect_text(payload)
    lower_text = text.lower()
    match_haystack = normalize_for_match(text)

    species_hits = []
    for species in SPECIES:
        for alias in species["aliases"]:
            if alias in lower_text:
                species_hits.append(
                    {
                        "canonical_name": species["canonical_name"],
                        "scientific_name": species["scientific_name"],
                        "group": species["group"],
                        "matched_alias": alias,
                    }
                )
                break

    jurisdiction_hits = []
    for alias, canonical in JURISDICTIONS.items():
        if alias in lower_text:
            jurisdiction_hits.append({"canonical_name": canonical, "matched_alias": alias})

    unit_hits = []
    for pattern, label, code in UNIT_PATTERNS:
        match = re.search(pattern, lower_text)
        if match:
            unit_hits.append(
                {"canonical_name": label, "code": code, "matched_text": match.group(0)}
            )

    id_tokens = []
    for pattern, code in ID_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            id_tokens.append(code)

    identity_slice, identity_records, identity_warnings = load_identity_slice()
    identity_hints = []
    if identity_records:
        for record in identity_records:
            hint = match_identity_record(record, match_haystack)
            if hint:
                identity_hints.append(hint)
        identity_hints = dedupe(identity_hints, "canonical_local_id")
    else:
        identity_warnings.append(
            "bounded Columbia Basin v0 identity slice is unavailable; identity hints are disabled"
        )

    warnings = []
    if not text:
        warnings.append("no free text supplied; normalization is limited to explicit fields")
    if not species_hits:
        warnings.append("no seeded species alias matched")
    if not unit_hits:
        warnings.append("no seeded management-unit system matched")
    if identity_records and not identity_hints:
        warnings.append("no Columbia Basin v0 identity hint matched")
    warnings.extend(identity_warnings)

    identity_slice_summary = None
    if identity_slice:
        scope = identity_slice.get("scope") if isinstance(identity_slice, dict) else None
        if isinstance(scope, dict):
            identity_slice_summary = {
                "slice_id": identity_slice.get("slice_id", "columbia-basin-v0"),
                "region": scope.get("region", "Columbia Basin"),
                "status": scope.get("status", "bounded"),
                "authority": scope.get("authority", "non-authoritative"),
                "record_count": len(identity_records),
                "assumption": scope.get("assumption", ""),
            }
        else:
            identity_slice_summary = {
                "slice_id": identity_slice.get("slice_id", "columbia-basin-v0"),
                "record_count": len(identity_records),
            }

    emit(
        {
            "ok": True,
            "source": "seed-normalizer",
            "identity_slice": identity_slice_summary,
            "input": payload,
            "species": dedupe(species_hits, "canonical_name"),
            "jurisdictions": dedupe(jurisdiction_hits, "canonical_name"),
            "unit_systems": dedupe(unit_hits, "code"),
            "id_tokens": sorted(set(id_tokens)),
            "identity_hints": identity_hints,
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
