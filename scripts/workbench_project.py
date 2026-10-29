"""Offline readers for private research exports and reviewable framework proposals.

No network, RDF writes, model calls, publication, or source mutation occurs here.
The project shape follows the workbench ResearchProject/SourceRecord contract.
Scientific claims and disclosure safety require review beyond these checks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys

from _workbench_readiness import optional_readiness

FORMAT = "salmon-research-project.v1"
FRAMEWORK_FORMAT = "salmon-research-framework.v1"
OUTPUTS = {"metadata", "workflow", "commons", "ontology", "crosswalk"}
PREVIEW_FIELDS = {"title", "question", "description", "hypothesis", "region", "spatialScale", "temporalScale"}


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def object_fields(value, strings, label):
    require(isinstance(value, dict), f"{label} must be an object")
    for key in strings.split():
        require(isinstance(value.get(key), str), f"{label}.{key} must be a string")


def array(value, label):
    require(isinstance(value, list), f"{label} must be an array")
    return value


def strings(value, label):
    require(all(isinstance(x, str) for x in array(value, label)), f"{label} must contain strings")


def instant(value, label):
    require(isinstance(value, str), f"{label} must be an ISO timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{label} must be an ISO timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, f"{label} requires a timezone")
    return parsed


def date(value, label):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), f"{label} must be YYYY-MM-DD")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"{label} must be a real date") from exc


def unique_ids(records, label):
    ids = [x.get("id") for x in records]
    require(all(isinstance(x, str) and x.strip() for x in ids), f"{label} needs nonempty IDs")
    require(len(ids) == len(set(ids)), f"{label} has duplicate IDs")


def validate_bundle(data, *, require_commitment=False):
    object_fields(data, "format exportedAt", "bundle")
    require(data["format"] == FORMAT, "unsupported bundle format")
    instant(data["exportedAt"], "exportedAt")
    strings(data.get("limitations"), "limitations")
    p = data.get("project")
    object_fields(p, "id title description question hypothesis region spatialScale temporalStart temporalEnd temporalScale ownerName createdAt updatedAt", "project")
    require(p["id"].strip() and p["title"].strip(), "project requires ID and title")
    require(type(p.get("revision")) is int and p["revision"] >= 0, "revision must be a nonnegative integer")
    saved = p["revision"] > 0
    if saved:
        require(p["ownerName"].strip(), "saved project requires ownerName")
    for key in ("createdAt", "updatedAt"):
        if saved or p[key]:
            instant(p[key], f"project.{key}")
    if require_commitment:
        require(saved, "contribution preview requires a saved project revision")
    for key in ("temporalStart", "temporalEnd"):
        if p[key]:
            date(p[key], key)
    if p["temporalStart"] and p["temporalEnd"]:
        require(p["temporalStart"] <= p["temporalEnd"], "temporal range is reversed")
    c = p.get("contribution")
    object_fields(c, "rawAccess embargoUntil reason", "contribution")
    require(type(c.get("committed")) is bool, "committed must be boolean")
    strings(c.get("outputs"), "contribution.outputs")
    require(set(c["outputs"]) <= OUTPUTS, "unsupported contribution output")
    require(len(c["outputs"]) == len(set(c["outputs"])), "duplicate contribution outputs")
    require(c["rawAccess"] == "private", "rawAccess must remain private")
    if c["embargoUntil"]:
        date(c["embargoUntil"], "embargoUntil")
    if c["committed"] or require_commitment:
        require(c["committed"] and c["outputs"], "a contribution commitment and outputs are required")
        date(c["embargoUntil"], "embargoUntil")
        require(c["reason"].strip(), "contribution reason is required")
    for x in array(p.get("datasets"), "project.datasets"):
        object_fields(x, "id title citation url status reason limitations evidence sourceType", "dataset")
        require(x["status"] in {"candidate", "included", "excluded", "deferred"}, "invalid source decision")
        if x["status"] != "candidate":
            require(x["reason"].strip(), "non-candidate source decision requires a reason")
        require(x["sourceType"] in {"catalog", "upload"}, "invalid sourceType")
        for k in ("sourceSha256", "originalFileName"):
            require(k not in x or isinstance(x[k], str), f"{k} must be a string")
        if x.get("sourceSha256"):
            require(re.fullmatch(r"[a-fA-F0-9]{64}", x["sourceSha256"]), "sourceSha256 must be SHA256")
        if "columns" in x:
            strings(x["columns"], "columns")
        if "rowCount" in x:
            require(type(x["rowCount"]) is int and x["rowCount"] >= 0, "invalid rowCount")
    unique_ids(p["datasets"], "datasets")
    for x in array(p.get("identities"), "project.identities"):
        object_fields(x, "id authority nativeId label entityType species sourceUrl sourceVersion targetAuthority targetId relationship evidence status reviewNote", "identity")
        require(x["relationship"] in {"lexical_alias", "published_relationship", "candidate_match"}, "invalid relationship")
        require(x["status"] in {"pending", "rejected"}, "identity cannot assert acceptance")
    unique_ids(p["identities"], "identities")
    for x in array(p.get("notes"), "project.notes"):
        object_fields(x, "id text createdAt author", "note")
        instant(x["createdAt"], "note.createdAt")
    unique_ids(p["notes"], "notes")
    for x in array(data.get("sources"), "sources"):
        object_fields(x, "id title organization kind phase years region description url license access limitations sourceVersion", "source")
        require(x["kind"] in {"Salmon", "Ocean", "Identity"}, "invalid source kind")
        require(x["phase"] in {"Coastal", "Offshore", "Regional"}, "invalid source phase")
        strings(x.get("variables"), "source.variables")
        require("doi" not in x or isinstance(x["doi"], str), "doi must be a string")
    unique_ids(data["sources"], "sources")
    return data


def inspect_bundle(data, as_of=None):
    validate_bundle(data)
    p = data["project"]
    today = date(as_of, "as_of") if as_of else instant(data["exportedAt"], "exportedAt").date()
    counts = {state: sum(x["status"] == state for x in p["datasets"]) for state in ("candidate", "included", "excluded", "deferred")}
    return {"format": "salmon-workbench-inspection.v1", "privacy": "private", "projectId": p["id"],
            "projectState": "unsaved_draft" if p["revision"] == 0 else "saved_revision_record",
            "declaredRevision": p["revision"], "persistenceVerified": False,
            "warnings": ["Unsaved draft: persistence and owner are not established."] if p["revision"] == 0 else [],
            "asOf": today.isoformat(), "sourceDecisions": counts, "sourceCatalogCount": len(data["sources"]),
            "pendingIdentityCount": sum(x["status"] == "pending" for x in p["identities"]),
            "embargoState": ("not_committed" if not p["contribution"]["committed"] else
                             "review_due" if date(p["contribution"]["embargoUntil"], "embargoUntil") <= today else "private_until_review"),
            "commitmentComplete": p["contribution"]["committed"],
            "optionalReadiness": optional_readiness(p),
            "publicationAuthorized": False, "scientificAcceptance": False,
            "limitations": ["Structural checks only; private notes and IDs are not contribution content.",
                            "Expiry requests review and never changes visibility.",
                            "Source inclusion and published relationships do not approve biological equivalence."]}


def framework_template(data):
    validate_bundle(data)
    return {"format": FRAMEWORK_FORMAT, "question": data["project"]["question"], "species": "", "unit": "",
            "lifeStage": "unknown", "cohortEvidence": [], "marineAgeEvidence": [],
            "evidenceType": "unknown", "survivalEvidence": [], "assignmentKind": "unknown",
            "usesAssignmentProbabilities": False, "exposures": [], "outcome": "",
            "spatialScale": data["project"]["spatialScale"], "temporalWindow": "",
            "alternatives": [], "sources": [], "limitations": ["Draft; no model, cohort alignment or scientific approval."]
            + (["Unsaved source project; persistence and owner are not established."] if data["project"]["revision"] == 0 else [])}


def supported_evidence(value, label):
    strings(value, label)
    require(value and all(x.strip().lower() not in {"", "unknown", "n/a", "not found", "none", "unverified"} for x in value), f"{label} requires explicit source evidence")


def validate_framework(data):
    object_fields(data, "format question species unit lifeStage evidenceType assignmentKind outcome spatialScale temporalWindow", "framework")
    require(data["format"] == FRAMEWORK_FORMAT, "unsupported framework format")
    require(data["lifeStage"] in {"unknown", "coastal", "first_winter", "winter_mixed", "whole_marine"}, "invalid lifeStage")
    require(data["evidenceType"] in {"unknown", "direct_survival", "encounter", "index", "proxy"}, "invalid evidenceType")
    require(data["assignmentKind"] in {"unknown", "hard_call", "probabilistic", "not_applicable"}, "invalid assignmentKind")
    for k in ("cohortEvidence", "marineAgeEvidence", "survivalEvidence", "exposures", "alternatives", "sources", "limitations"):
        strings(data.get(k), k)
    require(type(data.get("usesAssignmentProbabilities")) is bool, "usesAssignmentProbabilities must be boolean")
    require(not data["usesAssignmentProbabilities"] or data["assignmentKind"] == "probabilistic", "assignment probabilities are not established by hard calls or unknown assignments")
    if data["lifeStage"] == "first_winter":
        supported_evidence(data["marineAgeEvidence"], "marineAgeEvidence")
        supported_evidence(data["cohortEvidence"], "cohortEvidence")
    if data["evidenceType"] == "direct_survival":
        supported_evidence(data["survivalEvidence"], "survivalEvidence")
    return {"format": "salmon-framework-review.v1", "privacy": "private", "status": "awaiting_review", "scientificAcceptance": False,
            "framework": data, "unresolved": [k for k in ("species", "unit", "outcome", "spatialScale", "temporalWindow") if not data[k].strip()]
            + [k for k in ("lifeStage", "evidenceType", "assignmentKind") if data[k] == "unknown"],
            "limitations": ["Evidence strings are proposals, not independently verified ages, identities, survival or causal claims.", "No model was run and no RDF assertion was written."]}


def contribution_preview(data, sanitized):
    validate_bundle(data, require_commitment=True)
    require(isinstance(sanitized, dict) and sanitized, "provide explicitly selected sanitized fields")
    require(set(sanitized) <= PREVIEW_FIELDS, "unsupported disclosure field; notes, IDs, examples and raw data are excluded")
    require(all(isinstance(v, str) and v.strip() for v in sanitized.values()), "preview fields must contain nonempty text")
    return {"format": "salmon-contribution-preview.v1", "status": "disclosure_review_required", "publicationAuthorized": False,
            "selectedFields": dict(sorted(sanitized.items())), "limitations": ["User-supplied sanitized text still requires disclosure, rights and attribution review.", "No private project fields are copied automatically; no publication or external submission occurs."]}


def read_json(path):
    p = Path(path)
    require(not p.is_symlink() and p.is_file(), "input must be a regular local JSON file, not a symlink")
    require(p.stat().st_size <= 8_000_000, "JSON exceeds the 8 MB local contract limit")
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out
    def constant(value):
        raise ContractError(f"nonfinite JSON token: {value}")
    return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "framework-template", "framework-check", "contribution-preview"))
    parser.add_argument("--bundle")
    parser.add_argument("--framework")
    parser.add_argument("--sanitized")
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    try:
        if args.action == "framework-check":
            require(args.framework, "--framework is required")
            result = validate_framework(read_json(args.framework))
        else:
            require(args.bundle, "--bundle is required")
            data = read_json(args.bundle)
            if args.action == "inspect":
                result = inspect_bundle(data, args.as_of)
            elif args.action == "framework-template":
                result = framework_template(data)
            else:
                require(args.sanitized, "--sanitized is required; fields are never copied by default")
                result = contribution_preview(data, read_json(args.sanitized))
        print(json.dumps({"ok": True, **result}, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
