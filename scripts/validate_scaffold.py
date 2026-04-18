from __future__ import annotations

import json
import py_compile
import re
import subprocess
from pathlib import Path
from urllib import request


NON_PLATFORM_SKILLS = {
    "salmon-research-router-skill",
    "salmon-entity-normalizer-skill",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_string_list(value, label: str) -> None:
    require(isinstance(value, list), f"{label} must be a list")
    for item in value:
        require(isinstance(item, str) and item.strip(), f"{label} must contain non-empty strings")


def require_existing_path_or_url(repo_root: Path, value: str, label: str) -> None:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")
    if value.startswith("http://") or value.startswith("https://"):
        return
    require((repo_root / value).exists(), f"{label} references a missing path: {value}")


def validate_platform_registry(repo_root: Path, skill_names: list[str]) -> dict:
    registry_root = repo_root / "registry"
    vocab = load_json(registry_root / "vocab.json")
    platform_schema = load_json(registry_root / "platform-card.schema.json")
    identity_schema = load_json(registry_root / "identity-record.schema.json")
    skill_map = load_json(registry_root / "skill-platform-map.json")

    capability_categories = set(vocab["capability_categories"])
    capability_statuses = set(vocab["capability_statuses"])
    identity_entity_types = set(vocab["identity_entity_types"])
    mapping_relations = set(vocab["mapping_relations"])
    confidence_levels = set(vocab["confidence_levels"])
    identity_record_statuses = set(vocab["identity_record_statuses"])

    platform_cards: dict[str, dict] = {}
    for path in sorted((registry_root / "platforms").glob("*.json")):
        card = load_json(path)
        for field in platform_schema["required"]:
            require(field in card, f"platform card {path} missing field: {field}")
        require(card["platform_id"] == path.stem, f"platform_id mismatch in {path}")
        require(isinstance(card["platform_name"], str) and card["platform_name"].strip(), f"invalid platform_name in {path}")
        require(isinstance(card["owner"], str) and card["owner"].strip(), f"invalid owner in {path}")
        require_string_list(card["canonical_urls"], f"{path}: canonical_urls")
        require_string_list(card["docs_urls"], f"{path}: docs_urls")
        require(isinstance(card["auth_access_model"], str) and card["auth_access_model"].strip(), f"invalid auth_access_model in {path}")
        require_string_list(card["data_domains"], f"{path}: data_domains")
        require_string_list(card["identifier_systems"], f"{path}: identifier_systems")
        require_string_list(card["blockers"], f"{path}: blockers")
        require_string_list(card["governance_constraints"], f"{path}: governance_constraints")
        require_string_list(card["related_skills"], f"{path}: related_skills")
        require_string_list(card["evidence_links"], f"{path}: evidence_links")
        require_string_list(card["watch_fields"], f"{path}: watch_fields")
        require(isinstance(card["last_verified_date"], str) and DATE_RE.fullmatch(card["last_verified_date"]), f"invalid last_verified_date in {path}")

        capabilities = card["capabilities"]
        require(isinstance(capabilities, dict), f"{path}: capabilities must be an object")
        require(set(capabilities.keys()) == capability_categories, f"{path}: capabilities must cover every normalized category exactly once")
        for category, detail in capabilities.items():
            require(isinstance(detail, dict), f"{path}: capability {category} must be an object")
            require(detail.get("status") in capability_statuses, f"{path}: invalid capability status for {category}")
            require(isinstance(detail.get("note"), str) and detail["note"].strip(), f"{path}: capability {category} requires a note")

        for related_skill in card["related_skills"]:
            require(related_skill in skill_names, f"{path}: unknown related skill {related_skill}")

        platform_cards[card["platform_id"]] = card

    require(platform_cards, "registry/platforms must contain at least one platform card")

    mappings = skill_map.get("skills")
    require(isinstance(mappings, list) and mappings, "registry/skill-platform-map.json must contain a non-empty skills list")
    seen_mapped_skills: set[str] = set()
    for entry in mappings:
        require(isinstance(entry, dict), "each skill-platform mapping must be an object")
        skill = entry.get("skill")
        platform_id = entry.get("platform_id")
        kb_page = entry.get("kb_page")
        require(isinstance(skill, str) and skill.strip(), "skill-platform mapping requires skill")
        require(isinstance(platform_id, str) and platform_id.strip(), "skill-platform mapping requires platform_id")
        require(isinstance(kb_page, str) and kb_page.strip(), "skill-platform mapping requires kb_page")
        require(skill in skill_names, f"skill-platform mapping references unknown skill {skill}")
        require(platform_id in platform_cards, f"skill-platform mapping references unknown platform {platform_id}")
        require(skill not in seen_mapped_skills, f"duplicate skill-platform mapping for {skill}")
        seen_mapped_skills.add(skill)
        require(skill in platform_cards[platform_id]["related_skills"], f"platform card {platform_id} does not list mapped skill {skill}")
        require((repo_root / kb_page).exists(), f"mapped kb page does not exist: {kb_page}")

    expected_platform_skills = sorted(skill for skill in skill_names if skill not in NON_PLATFORM_SKILLS)
    require(sorted(seen_mapped_skills) == expected_platform_skills, "every external-source skill must map to exactly one platform card and kb page")

    identity_records = load_json(registry_root / "identity" / "seed-crosswalks.json")
    require(isinstance(identity_records, list) and identity_records, "registry/identity/seed-crosswalks.json must contain records")
    for index, record in enumerate(identity_records):
        label = f"identity record {index}"
        require(isinstance(record, dict), f"{label} must be an object")
        for field in identity_schema["required"]:
            require(field in record, f"{label} missing field: {field}")
        require(record["entity_type"] in identity_entity_types, f"{label} has invalid entity_type")
        require(record["mapping_relation"] in mapping_relations, f"{label} has invalid mapping_relation")
        require(record["confidence"] in confidence_levels, f"{label} has invalid confidence")
        require(record["record_status"] in identity_record_statuses, f"{label} has invalid record_status")
        for field in identity_schema["required"]:
            require(isinstance(record[field], str) and record[field].strip(), f"{label} field {field} must be a non-empty string")

    return {
        "platform_card_count": len(platform_cards),
        "mapped_external_skills": len(seen_mapped_skills),
        "identity_record_count": len(identity_records),
    }


def validate_skill_graph(repo_root: Path, skill_names: list[str]) -> dict:
    registry_root = repo_root / "registry"
    vocab = load_json(registry_root / "vocab.json")
    graph_schema = load_json(registry_root / "skill-graph.schema.json")
    graph = load_json(registry_root / "skill-graph.json")
    skill_map = load_json(registry_root / "skill-platform-map.json")

    node_required = graph_schema["properties"]["nodes"]["items"]["required"]
    edge_required = graph_schema["properties"]["edges"]["items"]["required"]
    node_types = set(vocab["skill_graph_node_types"])
    edge_relations = set(vocab["skill_graph_edge_relations"])
    platform_ids = {path.stem for path in (registry_root / "platforms").glob("*.json")}

    for field in graph_schema["required"]:
        require(field in graph, f"registry/skill-graph.json missing field: {field}")
    require(isinstance(graph["graph_version"], str) and graph["graph_version"].strip(), "registry/skill-graph.json graph_version must be a non-empty string")
    require(isinstance(graph["last_updated"], str) and DATE_RE.fullmatch(graph["last_updated"]), "registry/skill-graph.json last_updated must be a date")
    require(isinstance(graph["description"], str) and graph["description"].strip(), "registry/skill-graph.json description must be a non-empty string")

    nodes = graph["nodes"]
    edges = graph["edges"]
    require(isinstance(nodes, list) and nodes, "registry/skill-graph.json must contain nodes")
    require(isinstance(edges, list) and edges, "registry/skill-graph.json must contain edges")

    node_lookup: dict[str, dict] = {}
    lane_node_ids: set[str] = set()
    skill_node_names: set[str] = set()
    platform_node_ids: set[str] = set()

    for index, node in enumerate(nodes):
        label = f"skill-graph node {index}"
        require(isinstance(node, dict), f"{label} must be an object")
        for field in node_required:
            require(field in node, f"{label} missing field: {field}")
        node_id = node["id"]
        node_type = node["type"]
        require(isinstance(node_id, str) and node_id.strip(), f"{label} has invalid id")
        require(node_id not in node_lookup, f"duplicate skill-graph node id: {node_id}")
        require(node_type in node_types, f"{label} has invalid type: {node_type}")
        require(isinstance(node["label"], str) and node["label"].strip(), f"{label} has invalid label")
        require(isinstance(node["description"], str) and node["description"].strip(), f"{label} has invalid description")
        if "entrypoint" in node:
            require_existing_path_or_url(repo_root, node["entrypoint"], f"{label} entrypoint")
        if "lane_tags" in node:
            require_string_list(node["lane_tags"], f"{label} lane_tags")
        if node_type == "skill":
            require(node_id.startswith("skill:"), f"{label} must use a skill: prefix")
            skill_name = node_id.split(":", 1)[1]
            require(skill_name in skill_names, f"{label} references unknown skill {skill_name}")
            skill_node_names.add(skill_name)
        elif node_type == "platform":
            require(node_id.startswith("platform:"), f"{label} must use a platform: prefix")
            platform_id = node.get("platform_id")
            require(isinstance(platform_id, str) and platform_id in platform_ids, f"{label} has invalid platform_id")
            platform_node_ids.add(platform_id)
            if "platform_card" in node:
                require_existing_path_or_url(repo_root, node["platform_card"], f"{label} platform_card")
        elif node_type == "lane":
            require(node_id.startswith("lane:"), f"{label} must use a lane: prefix")
            lane_node_ids.add(node_id)
        elif node_type == "governance_tag":
            require(node_id.startswith("governance:"), f"{label} must use a governance: prefix")
        node_lookup[node_id] = node

    require(skill_node_names == set(skill_names), "skill graph must contain exactly one node for every repo skill")
    require(platform_node_ids == platform_ids, "skill graph must contain exactly one node for every platform card")
    require(lane_node_ids, "skill graph must contain at least one lane node")

    for node_id, node in node_lookup.items():
        for lane_tag in node.get("lane_tags", []):
            require(lane_tag in lane_node_ids, f"{node_id} references unknown lane tag {lane_tag}")

    expected_skill_platform_pairs = {
        (entry["skill"], entry["platform_id"])
        for entry in skill_map["skills"]
    }
    actual_skill_platform_pairs: set[tuple[str, str]] = set()
    lane_route_counts = {lane_id: 0 for lane_id in lane_node_ids}
    router_route_count = 0

    for index, edge in enumerate(edges):
        label = f"skill-graph edge {index}"
        require(isinstance(edge, dict), f"{label} must be an object")
        for field in edge_required:
            require(field in edge, f"{label} missing field: {field}")
        source = edge["source"]
        relation = edge["relation"]
        target = edge["target"]
        require(source in node_lookup, f"{label} references unknown source {source}")
        require(target in node_lookup, f"{label} references unknown target {target}")
        require(relation in edge_relations, f"{label} has invalid relation {relation}")
        require(isinstance(edge["rationale"], str) and edge["rationale"].strip(), f"{label} has invalid rationale")
        require_string_list(edge["evidence_refs"], f"{label} evidence_refs")
        for ref in edge["evidence_refs"]:
            require_existing_path_or_url(repo_root, ref, f"{label} evidence ref")

        source_type = node_lookup[source]["type"]
        target_type = node_lookup[target]["type"]

        if relation == "routes_to":
            require((source_type, target_type) in {("skill", "lane"), ("lane", "skill")}, f"{label} has invalid routes_to topology")
            if source == "skill:salmon-research-router-skill":
                router_route_count += 1
            if source_type == "lane":
                lane_route_counts[source] += 1
        elif relation in {"depends_on", "compose_with"}:
            require(source_type == "skill" and target_type == "skill", f"{label} must connect skill to skill")
        elif relation == "uses_platform":
            require(source_type == "skill" and target_type == "platform", f"{label} must connect skill to platform")
            actual_skill_platform_pairs.add((source.split(":", 1)[1], target.split(":", 1)[1]))
        elif relation == "constrained_by":
            require(source_type in {"skill", "platform", "lane"} and target_type == "governance_tag", f"{label} must point to a governance tag")

    require(router_route_count > 0, "skill graph must route from the router to at least one lane")
    require(all(count > 0 for count in lane_route_counts.values()), "every lane node must route to at least one skill")
    require(actual_skill_platform_pairs == expected_skill_platform_pairs, "skill graph uses_platform edges must match registry/skill-platform-map.json exactly")

    router_graph_ref = repo_root / "skills" / "salmon-research-router-skill" / "references" / "skill-graph-routing.md"
    require(router_graph_ref.exists(), "router graph routing reference is missing")
    router_skill_text = (repo_root / "skills" / "salmon-research-router-skill" / "SKILL.md").read_text(encoding="utf-8")
    require("skill-graph-routing.md" in router_skill_text, "router SKILL.md must link to the graph routing reference")

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "lane_count": len(lane_node_ids),
    }


def validate_kb(repo_root: Path) -> dict:
    kb_root = repo_root / "kb"
    required_paths = [
        kb_root / "AGENTS.md",
        kb_root / "index.md",
        kb_root / "log.md",
        kb_root / "platforms",
        kb_root / "concepts",
        kb_root / "gaps",
        kb_root / "workflows",
    ]
    for path in required_paths:
        require(path.exists(), f"kb artifact missing: {path}")

    log_text = (kb_root / "log.md").read_text(encoding="utf-8")
    require(re.search(r"^## \[\d{4}-\d{2}-\d{2}\] ", log_text, flags=re.MULTILINE) is not None, "kb/log.md must contain timestamped entries")

    platform_pages = sorted((kb_root / "platforms").glob("*.md"))
    concept_pages = sorted((kb_root / "concepts").glob("*.md"))
    gap_pages = sorted((kb_root / "gaps").glob("*.md"))
    workflow_pages = sorted((kb_root / "workflows").glob("*.md"))
    require(platform_pages, "kb/platforms must contain pages")
    require(concept_pages, "kb/concepts must contain pages")
    require(gap_pages, "kb/gaps must contain pages")
    require(workflow_pages, "kb/workflows must contain pages")

    platform_registry_root = repo_root / "registry" / "platforms"
    for page in platform_pages:
        text = page.read_text(encoding="utf-8")
        match = re.search(r"\.\./\.\./registry/platforms/([a-z0-9-]+)\.json", text)
        require(match is not None, f"{page} must link to its platform card")
        require((platform_registry_root / f"{match.group(1)}.json").exists(), f"{page} links to missing platform card")

    for page in gap_pages:
        text = page.read_text(encoding="utf-8")
        has_reference = "../platforms/" in text or "../concepts/" in text
        require(has_reference, f"{page} must point to at least one platform page or concept page")

    return {
        "platform_page_count": len(platform_pages),
        "concept_page_count": len(concept_pages),
        "gap_page_count": len(gap_pages),
        "workflow_page_count": len(workflow_pages),
    }


def validate_gap_register(repo_root: Path, categories: list[str]) -> None:
    text = (repo_root / "docs" / "platform-gap-register.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    capture = False
    section_lines: list[str] = []
    for line in lines:
        if line.startswith("## Platform Capability Categories Referenced"):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            section_lines.append(line)
    referenced = re.findall(r"`([a-z_]+)`", "\n".join(section_lines))
    require(referenced, "docs/platform-gap-register.md must list normalized platform capability categories")
    require(set(referenced) == set(categories), "docs/platform-gap-register.md category list must match registry/vocab.json")


def fetch_json(url: str):
    req = request.Request(url, headers={"Accept": "application/json, application/ld+json;q=0.9"}, method="GET")
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def check_ontology_surface(url: str, root_iri: str) -> dict:
    try:
        payload = fetch_json(url)
        require(isinstance(payload, list), f"{url} did not return a JSON-LD list")
        root = next(item for item in payload if isinstance(item, dict) and item.get("@id") == root_iri)
        version = None
        modified = None
        if "http://www.w3.org/2002/07/owl#versionInfo" in root:
            version = root["http://www.w3.org/2002/07/owl#versionInfo"][0]["@value"]
        if "http://purl.org/dc/terms/modified" in root:
            modified = root["http://purl.org/dc/terms/modified"][0]["@value"]
        return {"ok": True, "url": url, "version": version, "modified": modified}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)}


def check_metasalmon_surface() -> dict:
    try:
        proc = subprocess.run(
            [
                "Rscript",
                "-e",
                "if (requireNamespace('metasalmon', quietly = TRUE)) { cat(as.character(utils::packageVersion('metasalmon'))) } else { cat('NOT_INSTALLED') }",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        version = proc.stdout.strip()
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "Rscript failed"}
        if version == "NOT_INSTALLED" or not version:
            return {"ok": False, "error": "metasalmon is not installed"}
        return {"ok": True, "version": version}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def check_rmis_surface() -> dict:
    try:
        url = "https://www.rmis.org/include/rmis_announce.html"
        with request.urlopen(url, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
        version_match = re.search(r"Version\s+([0-9]+\.[0-9]+)\s+of the RMIS Database", html, flags=re.IGNORECASE)
        date_match = re.search(r"as of:\s*(.+?)\.", html, flags=re.IGNORECASE | re.DOTALL)
        effective_date = None
        if date_match:
            effective_date = re.sub(r"<[^>]+>", "", date_match.group(1))
            effective_date = " ".join(effective_date.split()) or None
        return {
            "ok": bool(version_match),
            "url": url,
            "version": version_match.group(1) if version_match else None,
            "effective_date": effective_date,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / ".codex-plugin" / "plugin.json"
    skills_root = repo_root / "skills"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_top = ["name", "version", "description", "skills", "interface"]
    missing = [key for key in required_top if key not in manifest]
    if missing:
        raise SystemExit(f"plugin manifest missing keys: {missing}")

    skill_names: list[str] = []
    python_files: list[Path] = []

    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise SystemExit(f"missing SKILL.md in {skill_dir}")
        skill_names.append(skill_dir.name)
        for path in skill_dir.rglob("*.py"):
            python_files.append(path)

    for path in sorted((repo_root / "scripts").glob("*.py")):
        python_files.append(path)

    for path in python_files:
        py_compile.compile(str(path), doraise=True)

    registry_stats = validate_platform_registry(repo_root, skill_names)
    skill_graph_stats = validate_skill_graph(repo_root, skill_names)
    kb_stats = validate_kb(repo_root)
    vocab = load_json(repo_root / "registry" / "vocab.json")
    validate_gap_register(repo_root, vocab["capability_categories"])

    watch_surface_checks = {
        "smn": check_ontology_surface(
            "https://salmon-data-mobilization.github.io/salmon-domain-ontology/smn.jsonld",
            "https://w3id.org/smn",
        ),
        "gcdfo": check_ontology_surface(
            "https://dfo-pacific-science.github.io/dfo-salmon-ontology/gcdfo.jsonld",
            "https://w3id.org/gcdfo/salmon",
        ),
        "metasalmon": check_metasalmon_surface(),
        "rmis": check_rmis_surface(),
    }
    warnings = [
        f"watch surface {name} check failed"
        for name, detail in watch_surface_checks.items()
        if not detail.get("ok")
    ]

    print(json.dumps({
        "ok": True,
        "manifest": str(manifest_path),
        "skill_count": len(skill_names),
        "skills": skill_names,
        "python_files_compiled": len(python_files),
        "registry": registry_stats,
        "skill_graph": skill_graph_stats,
        "kb": kb_stats,
        "watch_surface_checks": watch_surface_checks,
        "warnings": warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
