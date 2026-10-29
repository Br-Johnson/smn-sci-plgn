"""Redacted readiness counts for one pinned optional workbench export shape.

These observations never validate vocabulary membership, source bytes or
scientific fitness. Future shapes are left uninterpreted in the input file.
"""
from __future__ import annotations

import re

SOURCE_COMMIT = "dfdc7a98b3e3a7ffffe97399419f3c48dbf83932"
MODEL_FIELDS = {"schemaVersion", "concepts", "relationships", "bindings", "layout"}
CONCEPT_FIELDS = {"id", "label", "definition", "evidence", "uncertainty", "alternatives"}
IRI_FIELDS = {"termIri", "propertyIri", "entityIri", "unitIri", "constraintIri", "statisticalModifierIri"}
COLUMN_FIELDS = {"sourceId", "sourceSha256", "columnName", "conceptId", "columnRole", "valueType", "termType"} | IRI_FIELDS


def shape(value, fields):
    return isinstance(value, dict) and set(value) == fields


def records(value):
    return isinstance(value, list) and len(value) <= 500


def texts(row, fields):
    return shape(row, fields) and all(isinstance(v, str) for v in row.values())


def model_readiness(value):
    if value is None:
        return {"state": "absent"}
    if not isinstance(value, dict) or type(value.get("schemaVersion")) is not int:
        return {"state": "uninterpreted_shape"}
    if value["schemaVersion"] != 1:
        return {"state": "uninterpreted_version"}
    if not shape(value, MODEL_FIELDS) or not all(records(value[k]) for k in MODEL_FIELDS - {"schemaVersion"}):
        return {"state": "uninterpreted_shape"}
    if not all(texts(c, CONCEPT_FIELDS) for c in value["concepts"]):
        return {"state": "uninterpreted_shape"}
    if not all(texts(c, CONCEPT_FIELDS | {"fromConceptId", "toConceptId"}) for c in value["relationships"]):
        return {"state": "uninterpreted_shape"}
    binding_fields = {"id", "conceptId", "sourceId", "columnName"}
    if not all(isinstance(b, dict) and binding_fields <= set(b) <= binding_fields | {"sourceSha256"}
               and all(isinstance(v, str) for v in b.values()) for b in value["bindings"]):
        return {"state": "uninterpreted_shape"}
    if not all(shape(p, {"id", "x", "y"}) and isinstance(p["id"], str)
               and all(type(p[k]) in (int, float) for k in ("x", "y")) for p in value["layout"]):
        return {"state": "uninterpreted_shape"}
    return {"state": "awaiting_review", "counts": {
        "concepts": len(value["concepts"]), "relationships": len(value["relationships"]),
        "bindings": len(value["bindings"]),
        "conceptsMissingDefinition": sum(not c["definition"].strip() for c in value["concepts"]),
        "conceptsMissingEvidence": sum(not c["evidence"].strip() for c in value["concepts"]),
    }}


def annotation_readiness(value, sources):
    if value is None:
        return {"state": "absent"}
    if not isinstance(value, dict) or type(value.get("schemaVersion")) is not int:
        return {"state": "uninterpreted_shape"}
    if value["schemaVersion"] != 1:
        return {"state": "uninterpreted_version"}
    if (not shape(value, {"schemaVersion", "vocabulary", "columns"})
            or not texts(value["vocabulary"], {"id", "sha256"})
            or not records(value["columns"])
            or not all(texts(c, COLUMN_FIELDS) for c in value["columns"])):
        return {"state": "uninterpreted_shape"}
    def source_matches(column):
        matches = [s for s in sources if s["id"] == column["sourceId"]]
        return (len(matches) == 1 and bool(re.fullmatch(r"[a-f0-9]{64}", column["sourceSha256"]))
                and matches[0].get("sourceSha256") == column["sourceSha256"]
                and matches[0].get("columns", []).count(column["columnName"]) == 1)
    columns = value["columns"]
    vocabulary = value["vocabulary"]
    return {"state": "awaiting_review", "vocabularyPinRecorded": bool(
        vocabulary["id"].strip() and re.fullmatch(r"[a-f0-9]{64}", vocabulary["sha256"])),
        "vocabularyVerified": False, "counts": {
            "columns": len(columns),
            "columnsMissingRole": sum(not c["columnRole"].strip() for c in columns),
            "columnsMissingValueType": sum(not c["valueType"].strip() for c in columns),
            "columnsMissingTermKind": sum(not c["termType"].strip() for c in columns),
            "columnsWithoutTermSelections": sum(not any(c[k].strip() for k in IRI_FIELDS) for c in columns),
            "sourceBindingsMismatched": sum(not source_matches(c) for c in columns),
        }}


def optional_readiness(project):
    return {"sourceCommit": SOURCE_COMMIT, "schemaVersion": 1,
            "domainModel": model_readiness(project.get("domainModel")),
            "annotationDraft": annotation_readiness(project.get("annotationDraft"), project["datasets"]),
            "scientificAcceptance": False,
            "limitations": ["Readiness counts only; optional contents remain private and unapproved.",
                            "Unknown shapes and versions are preserved in the input and remain uninterpreted.",
                            "Source bytes, vocabulary membership and scientific meaning are not verified."]}
