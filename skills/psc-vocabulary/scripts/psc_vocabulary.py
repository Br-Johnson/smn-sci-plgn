"""Read an explicitly authorized, byte-pinned PSC catalog and release; no network."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from _common import emit, inline_credentials_refused, load_input, result_error  # noqa: E402

SOURCE_SCHEMA = "psc-vocabulary.source/v1"
PSC_BASE = "https://w3id.org/psc/vocab/concept/"
PROMOTION_PATH = "provenance/stock-recruit-measurements/promotion.json"
REQUIRED_INPUTS = {"concepts.csv", "external-concepts.csv", "concept-reuse.csv", "context-selections.csv",
                   "working-contexts.json", "external-mapping-review.csv"}


class SourceFailure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, message="The pinned source does not satisfy the supported PSC release/catalog contract."):
    if not condition:
        raise SourceFailure("source_invalid", message)


def pinned_bytes(path, expected):
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected))
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, "A source SHA-256 pin does not match; no results were read as authoritative.")
    return raw


def artifact_bytes(root, name):
    require(isinstance(name, str) and bool(name))
    relative = PurePosixPath(name)
    require(relative.parts and relative.as_posix() == name and not relative.is_absolute() and ".." not in relative.parts and "\\" not in name)
    current = root
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), "Release artifact symlinks are not supported.")
    return current.read_bytes()


def rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))


def indexed(records, key):
    result = {row[key]: row for row in records}
    require(len(result) == len(records), "Duplicate identities in the source are unsupported.")
    return result


def same_records(left, right):
    return sorted(json.dumps(row, sort_keys=True) for row in left) == sorted(json.dumps(row, sort_keys=True) for row in right)


def verify_catalog(catalog, files, version):
    """Check the discovery projection against the manifest-bound authoring rows."""
    local = indexed(rows(files["concepts.csv"]), "concept_id")
    external = indexed(rows(files["external-concepts.csv"]), "concept_iri")
    reuse = indexed(rows(files["concept-reuse.csv"]), "legacy_concept_id")
    selections = rows(files["context-selections.csv"])
    require(catalog["contexts"] == json.loads(files["working-contexts.json"]))
    expected = {}
    for identity, row in local.items():
        if identity in reuse:
            require(row["lifecycle_status"] == "deprecated" and row["replaced_by_iri"] == reuse[identity]["concept_iri"])
            require(reuse[identity]["concept_iri"] in external)
            continue
        expected[PSC_BASE + identity] = {"label": row["pref_label_en"], "definition": row["definition_en"],
                                         "scope_note": row["scope_note_en"], "source_id": "psc",
                                         "source_version": version, "source_status": row["status"]}
    for iri, row in external.items():
        require(iri not in expected)
        expected[iri] = {"label": row["pref_label_en"], "definition": row["definition_en"],
                         "scope_note": row["scope_note_en"], "source_id": row["source_id"],
                         "source_version": row["source_version"], "source_status": "source-defined",
                         "source_sha256": row["source_sha256"]}
    actual = indexed(catalog["terms"], "iri")
    require(actual.keys() == expected.keys(), "Catalog identities differ from the immutable release.")
    for iri, fields in expected.items():
        term = actual[iri]
        require(all(term[key] == value for key, value in fields.items()), "Catalog definitions, identity or source status differ from the immutable release.")
        aliases = [{"concept_id": identity, "label": local[identity]["pref_label_en"], "iri": PSC_BASE + identity}
                   for identity, row in reuse.items() if row["concept_iri"] == iri]
        require(same_records(term["aliases"], aliases))
        selected = [row for row in selections if row["concept_iri"] == iri]
        require(same_records(term["selections"], selected))
        require(term["contexts"] == sorted({row["context_id"] for row in selected}))
        require(term["scheme_ids"] == sorted({row["scheme_id"] for row in selected}))
        require(term["selection_statuses"] == (sorted({row["selection_status"] for row in selected}) or ["available"]))
    replacements = [{"legacy_iri": PSC_BASE + identity, "concept_iri": row["concept_iri"]} for identity, row in reuse.items()]
    require(same_records(catalog["legacy_replacements"], replacements))


def read_source(request):
    if request.get("authorized") is not True:
        raise SourceFailure("permission_refused", "Reading this source requires the user's authorization; do not infer access or approval from a path.")
    configured = request.get("source_config") or os.environ.get("PSC_VOCABULARY_SOURCE")
    if not isinstance(configured, str) or not configured:
        raise SourceFailure("source_unavailable", "No source is configured. Supply a reviewed local source_config or PSC_VOCABULARY_SOURCE.")
    descriptor = Path(configured).expanduser()
    config = json.loads(descriptor.read_bytes())
    require(config["schema_version"] == SOURCE_SCHEMA)
    require(isinstance(config["source_ref"], str) and bool(config["source_ref"]))
    release = descriptor.parent / config["release_directory"]
    require(not release.is_symlink())
    raw_manifest = pinned_bytes(release / "manifest.json", config["manifest_sha256"])
    manifest = json.loads(raw_manifest)
    require(manifest["schema_version"] == "1.0" and manifest["vocabulary_id"] == "psc-salmon-vocabularies")
    require(manifest["namespace"] == "https://w3id.org/psc/vocab/")
    require(manifest["version"] == config["release_version"])
    files = {}
    for artifact in manifest["artifacts"]:
        name = artifact["path"]
        require(name not in files)
        raw = artifact_bytes(release, name)
        require(hashlib.sha256(raw).hexdigest() == artifact["sha256"] and len(raw) == artifact["bytes"], "A release artifact hash or byte count differs from its pinned manifest.")
        files[name] = raw
    require(REQUIRED_INPUTS <= files.keys(), "The pinned release does not list all required discovery inputs.")
    catalog = json.loads(pinned_bytes(descriptor.parent / config["catalog_path"], config["catalog_sha256"]))
    require(catalog["schema_version"] == "2.0" and catalog["released_version"] == manifest["version"])
    verify_catalog(catalog, files, manifest["version"])
    provenance = {"source_ref": config["source_ref"], "release_version": manifest["version"],
                  "manifest_sha256": config["manifest_sha256"], "catalog_sha256": config["catalog_sha256"],
                  "all_artifact_hashes_verified": True, "artifact_count": len(files),
                  "release_status": manifest["status"], "issued": manifest["issued"]}
    return catalog, files, provenance


def discovery_record(term, files):
    local = indexed(rows(files["concepts.csv"]), "concept_id")
    reuse = [row for row in rows(files["concept-reuse.csv"]) if row["concept_iri"] == term["iri"]]
    identities = {row["legacy_concept_id"] for row in reuse}
    if term["iri"].startswith(PSC_BASE):
        identities.add(term["iri"][len(PSC_BASE):])
    stock_kind = any(local[identity]["scheme_id"] in {"stock-reference-kind", "stock-group-kind"} for identity in identities)
    mappings = [row | {"canonicalizes": False} for row in rows(files["external-mapping-review.csv"]) if row["subject_id"] in identities]
    review = {"term_status": term["source_status"], "domain_review_status": "not_asserted",
              "approval_status": "not_asserted", "adoption_status": "not_asserted"}
    if PROMOTION_PATH in files:
        promotion = json.loads(files[PROMOTION_PATH])
        require(promotion["schema_version"] == "1.0")
        if identities.intersection(promotion["concept_ids"]):
            review.update({key: promotion[key] for key in ("approval_status", "domain_review_status", "adoption_status")})
            review["promotion_record"] = promotion
    return term | {
        "identity_basis": "explicit_concept_reuse" if reuse else "released_source_iri",
        "legacy_records": [local[row["legacy_concept_id"]] for row in reuse],
        "reuse_decisions": reuse,
        "mapping_reviews": mappings,
        "review": review,
        "entity_role": "stock_kind" if stock_kind else "vocabulary_concept",
        "is_stock_record": False,
        "identity_note": "This names a kind of stock reference or grouping, never an individual stock record or its membership." if stock_kind else "A vocabulary concept; operational records and scientific approval are separate.",
    }


def handle(request):
    if not isinstance(request, dict):
        return result_error("invalid_input", "Expected one JSON object.")
    action = request.get("action", "lookup")
    if action == "runtime":
        return {"ok": True, "actions": ["runtime", "lookup"], "source_schema": SOURCE_SCHEMA,
                "catalog_schema": "2.0", "release_schema": "1.0", "network": False, "read_only": True}
    if action != "lookup" or not isinstance(request.get("query"), str) or not request["query"].strip():
        return result_error("invalid_input", "Use lookup with a nonempty query, or runtime.")
    if request.get("entity_role", "concept") != "concept":
        return result_error("unsupported_role", "This reader discovers vocabulary concepts, not individual stock records or memberships.")
    limit = request.get("max_items", 10)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        return result_error("invalid_input", "max_items must be an integer from 1 to 100.")
    try:
        catalog, files, provenance = read_source(request)
        query = request["query"].strip().casefold()
        results = []
        for term in catalog["terms"]:
            if query in " ".join([term["iri"], term["label"], term["definition"], *[alias["concept_id"] + " " + alias["label"] + " " + alias["iri"] for alias in term["aliases"]]]).casefold():
                results.append(discovery_record(term, files))
        return {"ok": True, "status": "available", "source": provenance, "results": results[:limit], "total": len(results)}
    except SourceFailure as exc:
        return result_error(exc.code, str(exc), status="unavailable")
    except OSError:
        return result_error("source_unavailable", "The configured local source cannot be read. No absence or ontology-gap claim is justified.", status="unavailable")
    except (KeyError, TypeError, ValueError, UnicodeError, csv.Error):
        return result_error("source_invalid", "The configured source is malformed or unsupported; no authoritative results are available.", status="unavailable")


if __name__ == "__main__":
    try:
        payload = load_input()
        if not isinstance(payload, dict) or not inline_credentials_refused(payload):
            emit(handle(payload))
    except (ValueError, TypeError):
        emit(result_error("invalid_input", "Expected one JSON object on stdin."))
