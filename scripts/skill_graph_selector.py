from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

LANE_PRIORITY = [
    "lane:stock-assessment",
    "lane:crosswalk-harmonization",
    "lane:ontology-semantic-resolution",
    "lane:telemetry-passage",
    "lane:coded-wire-tag-recovery",
    "lane:watershed-connectivity",
    "lane:literature-reports-dataset-discovery",
    "lane:hatchery-harvest-management",
    "lane:genetics-stock-identification",
    "lane:climate-ocean-context",
    "lane:package-metadata-validation",
]

LANE_PATTERNS: dict[str, tuple[str, ...]] = {
    "lane:stock-assessment": (
        r"\bstock\b",
        r"\bassessment\b",
        r"\babundance\b",
        r"\btrend\b",
        r"\bstatus\b",
        r"\bescapement\b",
        r"\brun size\b",
        r"\brecruitment\b",
        r"\bpopulation\b",
    ),
    "lane:crosswalk-harmonization": (
        r"\bcrosswalk\b",
        r"\bcritfc\b",
        r"\bhuc6\b",
        r"\bharmoniz(?:e|ation)\b",
        r"\breconcile\b",
        r"\bmapp(?:ing|ed)\b",
        r"\bequivalent units?\b",
    ),
    "lane:ontology-semantic-resolution": (
        r"\bontology\b",
        r"\bterm\b",
        r"\bconcept\b",
        r"\biri\b",
        r"\blabel\b",
        r"\bdefinition\b",
        r"\bsynonym\b",
        r"\bsemantic\b",
        r"\bvocab(?:ulary)?\b",
    ),
    "lane:telemetry-passage": (
        r"\btelemetry\b",
        r"\bpassage\b",
        r"\bmigration\b",
        r"\bsurvival\b",
        r"\bpit[- ]?tag\b",
        r"\bptagis\b",
        r"\btag detections?\b",
        r"\bdetection\b",
    ),
    "lane:coded-wire-tag-recovery": (
        r"\bcoded[- ]wire[- ]tag\b",
        r"\bcwt\b",
        r"\brmis\b",
        r"\brecover(?:y|ies)\b",
        r"\btag return\b",
        r"\bwire tag\b",
    ),
    "lane:watershed-connectivity": (
        r"\bwatershed\b",
        r"\bbasin\b",
        r"\bconnectiv(?:ity|e)\b",
        r"\bconnected\b",
        r"\bbarrier\b",
        r"\btributary\b",
        r"\bnetwork\b",
        r"\bdrainage\b",
        r"\bcatchment\b",
    ),
    "lane:literature-reports-dataset-discovery": (
        r"\bliterature\b",
        r"\bpaper(?:s)?\b",
        r"\breport(?:s)?\b",
        r"\bdataset(?:s)?\b",
        r"\bpubmed\b",
        r"\bstudy\b",
        r"\bevidence\b",
        r"\bsearch\b",
        r"\bdiscover(?:y|ing)?\b",
    ),
    "lane:hatchery-harvest-management": (
        r"\bhatchery\b",
        r"\bharvest\b",
        r"\bfishery\b",
        r"\bbroodstock\b",
        r"\brelease\b",
        r"\bcatch samples?\b",
        r"\bfishery catch\b",
        r"\ballocation\b",
        r"\bquota\b",
    ),
    "lane:genetics-stock-identification": (
        r"\bgenetic(?:s)?\b",
        r"\bgsi\b",
        r"\bstock identification\b",
        r"\bmixed stock\b",
        r"\bancestry\b",
        r"\bdna\b",
        r"\bsnp\b",
        r"\bmicrosatellite\b",
    ),
    "lane:climate-ocean-context": (
        r"\bclimate\b",
        r"\bocean\b",
        r"\btemperature\b",
        r"\bupwelling\b",
        r"\benso\b",
        r"\bpdo\b",
        r"\bmarine heatwave\b",
        r"\bsalinity\b",
    ),
    "lane:package-metadata-validation": (
        r"\bpackage\b",
        r"\bdatapackage\b",
        r"\bmetadata\b",
        r"\bvalidate\b",
        r"\bvalidation\b",
        r"\bmetasalmon\b",
        r"\bschema\b",
    ),
}

NORMALIZATION_ONLY_PATTERNS = (
    r"\bnormalize\b",
    r"\bnormalise\b",
    r"\balias(?:es)?\b",
    r"\bequivalent\b",
    r"\bsame as\b",
    r"\bmanagement unit\b",
    r"\bunit system\b",
    r"\bspecies name\b",
    r"\bjurisdiction\b",
)

DFO_PATTERNS = (
    r"\bdfo\b",
    r"\bgcdfo\b",
    r"\bfisheries and oceans\b",
    r"\bcanadian\b",
    r"\bcanada\b",
    r"\bprofile-specific\b",
    r"\borganization profile\b",
    r"\borganization-specific\b",
)

NO_AUTH_PATTERNS = (
    r"\bwithout credentials\b",
    r"\bwithout a key\b",
    r"\bno key\b",
    r"\bno api key\b",
    r"\bno token\b",
    r"\bwithout a bearer token\b",
    r"\bunauthenticated\b",
    r"\bpublic-only\b",
    r"\bpublic only\b",
    r"\bno auth\b",
    r"\bwithout auth\b",
)

GAP_PATTERNS = (
    r"what is still missing from the salmon platform",
    r"what's missing from the salmon platform",
    r"what is missing from the salmon platform",
    r"\bplatform gaps?\b",
    r"\bbehavioral validation\b",
    r"\bmissing\b.*\bplatform\b",
    r"\bthin coverage\b",
    r"\bno wrapper\b",
    r"\bunsupported\b",
)

GAP_LANES = [
    "lane:identity-graph",
    "lane:nuseeds-wrapper",
    "lane:hatchery-registry",
    "lane:behavioral-validation",
    "lane:composite-workflows",
]

NORMALIZER_LANES = {
    "lane:stock-assessment",
    "lane:crosswalk-harmonization",
    "lane:telemetry-passage",
    "lane:watershed-connectivity",
    "lane:coded-wire-tag-recovery",
    "lane:hatchery-harvest-management",
}

LANE_SKILL_MAP: dict[str, tuple[str, ...]] = {
    "lane:stock-assessment": ("salmon-entity-normalizer-skill", "streamnet-api-skill", "salmon-literature-skill"),
    "lane:crosswalk-harmonization": ("salmon-entity-normalizer-skill", "critfc-crosswalk-skill"),
    "lane:telemetry-passage": ("salmon-entity-normalizer-skill", "ptagis-skill", "dart-query-skill"),
    "lane:watershed-connectivity": ("salmon-entity-normalizer-skill", "dart-query-skill", "streamnet-api-skill", "salmon-literature-skill"),
    "lane:hatchery-harvest-management": ("salmon-entity-normalizer-skill", "rmis-skill", "salmon-literature-skill"),
    "lane:coded-wire-tag-recovery": ("salmon-entity-normalizer-skill", "rmis-skill"),
    "lane:genetics-stock-identification": ("salmon-literature-skill",),
    "lane:climate-ocean-context": ("salmon-literature-skill",),
    "lane:literature-reports-dataset-discovery": ("salmon-literature-skill",),
    "lane:ontology-semantic-resolution": ("smn-ontology-skill",),
    "lane:package-metadata-validation": ("smn-ontology-skill", "metasalmon-skill"),
}

SPECIAL_SKILL_COMPANIONS: dict[str, tuple[str, ...]] = {
    "smn-ontology-skill": (),
    "gcdfo-ontology-skill": ("smn-ontology-skill",),
    "metasalmon-skill": ("smn-ontology-skill",),
    "ptagis-skill": ("dart-query-skill",),
    "streamnet-api-skill": ("salmon-literature-skill",),
    "rmis-skill": ("salmon-literature-skill",),
}

OPTIONAL_SKILL_PATTERNS: dict[str, tuple[str, ...]] = {
    "noaa-sps-skill": (
        r"\bsps\b",
        r"\bsalmon population summary\b",
        r"\brecovery domain\b",
        r"\bmajor population group\b",
        r"\bmpg\b",
        r"\besa-listed\b",
        r"\brecovery planning\b",
    ),
    "npafc-skill": (
        r"\bnpafc\b",
        r"\bcatalog(?:ue)?\b",
        r"\bstatistics\b",
        r"\bdataset(?:s)?\b",
        r"\bdownload(?:s|able)?\b",
        r"\bckan\b",
        r"\bcatch statistics\b",
        r"\bhatchery release statistics\b",
    ),
    "salmon-stock-brief-workflow-skill": (
        r"\bstock brief\b",
        r"\bstructured brief\b",
        r"\bmanagement brief\b",
    ),
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def compile_patterns(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns]


def contains_any(text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def match_count(text: str, patterns: Iterable[re.Pattern[str]]) -> tuple[int, list[str]]:
    matches: list[str] = []
    count = 0
    for pattern in patterns:
        if pattern.search(text):
            count += 1
            matches.append(pattern.pattern)
    return count, matches


@dataclass(frozen=True)
class GraphIndex:
    graph_version: str
    lane_order: list[str]
    lane_to_skills: dict[str, list[str]]
    skill_to_platform: dict[str, str]
    platform_cards: dict[str, dict]


def load_graph_index(repo_root: Path = REPO_ROOT) -> GraphIndex:
    graph = load_json(repo_root / "registry" / "skill-graph.json")
    platform_cards = {path.stem: load_json(path) for path in sorted((repo_root / "registry" / "platforms").glob("*.json"))}

    lane_order: list[str] = []
    lane_to_skills: dict[str, list[str]] = {}
    skill_to_platform: dict[str, str] = {}

    for node in graph["nodes"]:
        node_id = node["id"]
        if node["type"] == "lane":
            lane_order.append(node_id)
            lane_to_skills.setdefault(node_id, [])

    for edge in graph["edges"]:
        if edge["relation"] == "routes_to" and edge["source"] in lane_to_skills:
            lane_to_skills[edge["source"]].append(edge["target"].split(":", 1)[1])
        elif edge["relation"] == "uses_platform" and edge["source"].startswith("skill:") and edge["target"].startswith("platform:"):
            skill_to_platform[edge["source"].split(":", 1)[1]] = edge["target"].split(":", 1)[1]

    return GraphIndex(
        graph_version=graph["graph_version"],
        lane_order=lane_order,
        lane_to_skills=lane_to_skills,
        skill_to_platform=skill_to_platform,
        platform_cards=platform_cards,
    )


def platform_is_gated(platform_card: dict) -> bool:
    access_tier = str(platform_card.get("access_tier", "")).strip().lower()
    if access_tier in {"credentialed", "project_gated"}:
        return True
    if access_tier in {"public", "mixed"}:
        return False
    auth_text = " ".join(
        [
            str(platform_card.get("auth_access_model", "")),
            " ".join(platform_card.get("governance_constraints", [])),
            " ".join(
                f"{name} {detail.get('status', '')} {detail.get('note', '')}"
                for name, detail in platform_card.get("capabilities", {}).items()
                if isinstance(detail, dict)
            ),
        ]
    ).lower()
    public_markers = (
        "no auth requirement",
        "without credentials",
        "without a credential",
        "public and readable",
        "public page surfaces",
        "public e-utilities",
        "no private auth requirement",
        "no authorization requirement",
    )
    if any(marker in auth_text for marker in public_markers):
        return False
    return any(
        marker in auth_text
        for marker in (
            "auth-required",
            "bearer token",
            "api key",
            "api-key",
            "api_key",
            "credential-gated",
            "credentials required",
            "requires auth",
            "requires authentication",
            "authorization token",
            "auth token",
        )
    )


def is_no_auth_request(text: str) -> bool:
    return contains_any(text, compile_patterns(NO_AUTH_PATTERNS))


def is_dfo_request(text: str) -> bool:
    return contains_any(text, compile_patterns(DFO_PATTERNS))


def is_normalization_request(text: str) -> bool:
    return contains_any(text, compile_patterns(NORMALIZATION_ONLY_PATTERNS))


def is_gap_request(text: str) -> bool:
    return contains_any(text, compile_patterns(GAP_PATTERNS))


def seed_lanes(text: str, index: GraphIndex) -> tuple[list[str], list[str]]:
    scored: list[tuple[int, int, str, list[str]]] = []
    compiled = {lane: compile_patterns(patterns) for lane, patterns in LANE_PATTERNS.items()}
    for lane_id in index.lane_order:
        patterns = compiled.get(lane_id, [])
        score, matches = match_count(text, patterns)
        if score > 0:
            priority = LANE_PRIORITY.index(lane_id) if lane_id in LANE_PRIORITY else len(LANE_PRIORITY)
            scored.append((score, priority, lane_id, matches))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))

    seeded: list[str] = []
    reasons: list[str] = []
    for score, _, lane_id, matches in scored[:3]:
        seeded.append(lane_id)
        reasons.append(f"Seeded {lane_id} from cues: {', '.join(_summarize_patterns(matches))}")
    return seeded, reasons


def _summarize_patterns(patterns: Iterable[str]) -> list[str]:
    summary: list[str] = []
    for pattern in patterns:
        if "\\b" in pattern:
            cleaned = pattern.replace("\\b", "").replace("?:", "")
        else:
            cleaned = pattern
        cleaned = cleaned.replace("\\", "")
        summary.append(cleaned.strip("^$"))
    return summary


def add_skill(skill_name: str, selected: list[str], reasons: list[str], reason: str) -> None:
    if skill_name not in selected:
        selected.append(skill_name)
        reasons.append(reason)


def expand_selected_skills(text: str, seeded_lanes: list[str], index: GraphIndex) -> tuple[list[str], list[str], list[str]]:
    selected: list[str] = []
    blocked: list[str] = []
    reasons: list[str] = []

    dfo_specific = is_dfo_request(text)
    no_auth = is_no_auth_request(text)
    normalization_only = is_normalization_request(text) and not seeded_lanes

    if normalization_only:
        add_skill(
            "salmon-entity-normalizer-skill",
            selected,
            reasons,
            "Selected salmon-entity-normalizer-skill because the request is a normalization-only shape.",
        )
        return selected, blocked, reasons

    if any(lane in NORMALIZER_LANES for lane in seeded_lanes):
        add_skill(
            "salmon-entity-normalizer-skill",
            selected,
            reasons,
            "Selected salmon-entity-normalizer-skill because the seeded lane benefits from entity normalization.",
        )

    for lane_id in seeded_lanes:
        lane_skills = list(LANE_SKILL_MAP.get(lane_id, ()))
        if lane_id == "lane:ontology-semantic-resolution" and dfo_specific:
            lane_skills.append("gcdfo-ontology-skill")
        elif lane_id == "lane:package-metadata-validation" and dfo_specific:
            lane_skills.append("gcdfo-ontology-skill")

        for skill_name in lane_skills:
            if skill_name == "gcdfo-ontology-skill" and "smn-ontology-skill" not in selected:
                add_skill(
                    "smn-ontology-skill",
                    selected,
                    reasons,
                    "Selected smn-ontology-skill as the shared-term dependency for DFO-specific ontology or package work.",
                )

            if skill_name == "metasalmon-skill" and "smn-ontology-skill" not in selected:
                add_skill(
                    "smn-ontology-skill",
                    selected,
                    reasons,
                    "Selected smn-ontology-skill first because metasalmon depends on the shared ontology layer.",
                )

            add_skill(
                skill_name,
                selected,
                reasons,
                f"Selected {skill_name} from {lane_id}.",
            )

            for companion in SPECIAL_SKILL_COMPANIONS.get(skill_name, ()):
                if companion == "smn-ontology-skill" and lane_id == "lane:package-metadata-validation":
                    continue
                if companion == "salmon-literature-skill" and lane_id not in {
                    "lane:stock-assessment",
                    "lane:watershed-connectivity",
                    "lane:hatchery-harvest-management",
                    "lane:telemetry-passage",
                }:
                    continue
                if companion == "dart-query-skill" and lane_id != "lane:telemetry-passage":
                    continue
                if companion == "smn-ontology-skill" and skill_name == "gcdfo-ontology-skill":
                    continue
                add_skill(
                    companion,
                    selected,
                    reasons,
                    f"Selected {companion} because it is the graph companion for {skill_name}.",
                )

    optional_patterns = {
        skill: compile_patterns(patterns)
        for skill, patterns in OPTIONAL_SKILL_PATTERNS.items()
    }
    if seeded_lanes and contains_any(text, optional_patterns["noaa-sps-skill"]) and "lane:stock-assessment" in seeded_lanes:
        add_skill(
            "noaa-sps-skill",
            selected,
            reasons,
            "Selected noaa-sps-skill because the request references SPS-style population summary or recovery-planning cues.",
        )
    if seeded_lanes and contains_any(text, optional_patterns["npafc-skill"]) and "lane:literature-reports-dataset-discovery" in seeded_lanes:
        add_skill(
            "npafc-skill",
            selected,
            reasons,
            "Selected npafc-skill because the request explicitly mentions catalogue, dataset, statistics, or NPAFC cues.",
        )
    if seeded_lanes and contains_any(text, optional_patterns["salmon-stock-brief-workflow-skill"]) and "lane:stock-assessment" in seeded_lanes:
        add_skill(
            "salmon-stock-brief-workflow-skill",
            selected,
            reasons,
            "Selected salmon-stock-brief-workflow-skill because the user asked for a structured stock brief.",
        )

    if no_auth:
        for skill_name in list(selected):
            platform_id = index.skill_to_platform.get(skill_name)
            platform_card = index.platform_cards.get(platform_id or "", {})
            if platform_id and platform_is_gated(platform_card):
                selected.remove(skill_name)
                if skill_name not in blocked:
                    blocked.append(skill_name)
                reasons.append(
                    f"Blocked {skill_name} because the request asks for no-auth access and {platform_id} is credential-gated."
                )

    return selected, blocked, reasons


def select_graph_decision(request_text: str, repo_root: Path = REPO_ROOT) -> dict:
    index = load_graph_index(repo_root)
    text = request_text.strip().lower()
    seeded_lanes, seed_reasons = seed_lanes(text, index)

    if is_gap_request(text) and not seeded_lanes:
        reasons = [
            "Detected a gap/missing-coverage request and surfaced the scaffold gaps recorded in the repo docs.",
        ]
        return {
            "seeded_lanes": [],
            "selected_skills": [],
            "blocked_skills": [],
            "unsupported_lanes": GAP_LANES,
            "reasons": reasons,
        }

    selected_skills, blocked_skills, selection_reasons = expand_selected_skills(text, seeded_lanes, index)

    if not seeded_lanes and not selected_skills and not blocked_skills and not is_gap_request(text):
        selection_reasons.append(
            "No lane cues matched the current graph; returning an empty decision."
        )

    if is_gap_request(text) and seeded_lanes:
        selection_reasons.append(
            "The request also mentioned gaps, but lane cues were strong enough to keep the graph route."
        )

    reasons = seed_reasons + selection_reasons

    return {
        "seeded_lanes": seeded_lanes,
        "selected_skills": selected_skills,
        "blocked_skills": blocked_skills,
        "unsupported_lanes": [],
        "reasons": reasons,
    }


def _read_request_text(args: argparse.Namespace) -> str:
    if args.request is not None:
        return args.request
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    raise SystemExit("provide a request string with --request or via stdin")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select a routed skill subgraph for a salmon request.")
    parser.add_argument("--request", help="Request text to route.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repository root containing registry/ and scripts/.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON decision.")
    args = parser.parse_args(argv)

    decision = select_graph_decision(_read_request_text(args), repo_root=args.repo_root)
    if args.pretty:
        print(json.dumps(decision, indent=2, sort_keys=False))
    else:
        print(json.dumps(decision, separators=(",", ":"), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
