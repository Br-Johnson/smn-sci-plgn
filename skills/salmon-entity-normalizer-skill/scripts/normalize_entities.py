from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, load_input, result_error


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

    text_parts = [
        str(payload.get("text", "")),
        str(payload.get("species", "")),
        str(payload.get("jurisdiction", "")),
        " ".join(str(x) for x in payload.get("entity_ids", []) if x is not None),
    ]
    text = " ".join(part for part in text_parts if part).strip()
    lower_text = text.lower()

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

    warnings = []
    if not text:
        warnings.append("no free text supplied; normalization is limited to explicit fields")
    if not species_hits:
        warnings.append("no seeded species alias matched")
    if not unit_hits:
        warnings.append("no seeded management-unit system matched")

    emit(
        {
            "ok": True,
            "source": "seed-normalizer",
            "input": payload,
            "species": dedupe(species_hits, "canonical_name"),
            "jurisdictions": dedupe(jurisdiction_hits, "canonical_name"),
            "unit_systems": dedupe(unit_hits, "code"),
            "id_tokens": sorted(set(id_tokens)),
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
