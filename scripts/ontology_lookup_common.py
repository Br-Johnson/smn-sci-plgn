from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib import request


RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
RDFS_DOMAIN = "http://www.w3.org/2000/01/rdf-schema#domain"
RDFS_RANGE = "http://www.w3.org/2000/01/rdf-schema#range"
RDFS_IS_DEFINED_BY = "http://www.w3.org/2000/01/rdf-schema#isDefinedBy"
RDFS_SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
SKOS_PREF_LABEL = "http://www.w3.org/2004/02/skos/core#prefLabel"
SKOS_ALT_LABEL = "http://www.w3.org/2004/02/skos/core#altLabel"
SKOS_DEFINITION = "http://www.w3.org/2004/02/skos/core#definition"
SKOS_BROADER = "http://www.w3.org/2004/02/skos/core#broader"
IAO_DEFINITION = "http://purl.obolibrary.org/obo/IAO_0000115"
DCTERMS_DESCRIPTION = "http://purl.org/dc/terms/description"
DCTERMS_MODIFIED = "http://purl.org/dc/terms/modified"
DCTERMS_TITLE = "http://purl.org/dc/terms/title"
OWL_VERSION_INFO = "http://www.w3.org/2002/07/owl#versionInfo"
OWL_VERSION_IRI = "http://www.w3.org/2002/07/owl#versionIRI"
OWL_IMPORTS = "http://www.w3.org/2002/07/owl#imports"


def _iter_values(value: Any):
    if value is None:
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_values(item)
        return
    if isinstance(value, dict):
        if "@value" in value:
            yield str(value["@value"])
            return
        if "@id" in value:
            yield str(value["@id"])
            return
        if "@list" in value:
            yield from _iter_values(value["@list"])
            return
        return
    yield str(value)


def text_values(obj: dict[str, Any], key: str) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in _iter_values(obj.get(key)):
        cleaned = " ".join(item.split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            values.append(cleaned)
    return values


def first_text(obj: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        values = text_values(obj, key)
        if values:
            return values[0]
    return None


def local_name(iri: str, namespace_prefix: str, root_id: str) -> str:
    if iri == root_id:
        return ""
    if iri.startswith(namespace_prefix):
        return iri[len(namespace_prefix):]
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rsplit("/", 1)[-1]


def load_jsonld_document(
    *,
    env_value: str | None,
    candidates: list[str],
    timeout: int = 20,
) -> tuple[list[dict[str, Any]], str]:
    search_order: list[str] = []
    if env_value:
        search_order.append(env_value)
    search_order.extend(candidates)

    errors: list[dict[str, str]] = []
    for candidate in search_order:
        try:
            if candidate.startswith(("http://", "https://")):
                req = request.Request(
                    candidate,
                    headers={"Accept": "application/ld+json, application/json;q=0.9, */*;q=0.1"},
                    method="GET",
                )
                with request.urlopen(req, timeout=timeout) as response:
                    raw = response.read().decode("utf-8", errors="replace")
            else:
                raw = Path(candidate).expanduser().read_text(encoding="utf-8")
            payload = json.loads(raw)
            if not isinstance(payload, list):
                raise ValueError("expected JSON-LD top-level list")
            return payload, candidate
        except Exception as exc:  # noqa: BLE001
            errors.append({"candidate": candidate, "error": str(exc)})
    raise RuntimeError(json.dumps(errors, indent=2))


def normalize_record(
    obj: dict[str, Any],
    *,
    namespace_prefix: str,
    root_id: str,
) -> dict[str, Any]:
    iri = str(obj.get("@id", ""))
    return {
        "iri": iri,
        "local_name": local_name(iri, namespace_prefix, root_id),
        "label": first_text(obj, RDFS_LABEL, DCTERMS_TITLE, SKOS_PREF_LABEL),
        "pref_label": first_text(obj, SKOS_PREF_LABEL),
        "alt_labels": text_values(obj, SKOS_ALT_LABEL),
        "definition": first_text(obj, IAO_DEFINITION, SKOS_DEFINITION, DCTERMS_DESCRIPTION),
        "comment": first_text(obj, RDFS_COMMENT),
        "types": text_values(obj, "@type"),
        "broader": text_values(obj, SKOS_BROADER),
        "subclass_of": text_values(obj, RDFS_SUBCLASS_OF),
        "domain": text_values(obj, RDFS_DOMAIN),
        "range": text_values(obj, RDFS_RANGE),
        "is_defined_by": text_values(obj, RDFS_IS_DEFINED_BY),
    }


def ontology_metadata(
    data: list[dict[str, Any]],
    *,
    root_id: str,
    namespace_prefix: str,
) -> dict[str, Any]:
    root = next((obj for obj in data if obj.get("@id") == root_id), {})
    return {
        "root_iri": root_id,
        "label": first_text(root, RDFS_LABEL, DCTERMS_TITLE),
        "description": first_text(root, RDFS_COMMENT, DCTERMS_DESCRIPTION, IAO_DEFINITION),
        "version": first_text(root, OWL_VERSION_INFO),
        "version_iri": first_text(root, OWL_VERSION_IRI),
        "modified": first_text(root, DCTERMS_MODIFIED),
        "imports": text_values(root, OWL_IMPORTS),
        "namespace_term_count": sum(
            1
            for obj in data
            if isinstance(obj, dict)
            and str(obj.get("@id", "")).startswith(namespace_prefix)
            and (RDFS_LABEL in obj or SKOS_PREF_LABEL in obj or DCTERMS_TITLE in obj)
        ),
    }


def _score_record(record: dict[str, Any], query: str) -> int:
    q = query.strip().lower()
    if not q:
        return 0

    labels = [record.get("label") or "", record.get("pref_label") or "", record.get("local_name") or ""]
    labels.extend(record.get("alt_labels") or [])
    labels = [item.lower() for item in labels if item]
    iri = (record.get("iri") or "").lower()
    definition = ((record.get("definition") or "") + " " + (record.get("comment") or "")).lower()

    if q in {item for item in labels if item}:
        return 100
    if any(item.startswith(q) for item in labels if item):
        return 85
    if re.search(rf"\b{re.escape(q)}\b", " ".join(labels)):
        return 75
    if q in " ".join(labels):
        return 65
    if q in iri:
        return 55
    if q in definition:
        return 45
    return 0


def search_terms(
    data: list[dict[str, Any]],
    *,
    query: str,
    namespace_prefix: str,
    root_id: str,
    include_imports: bool = False,
    max_items: int = 10,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for obj in data:
        iri = str(obj.get("@id", ""))
        if iri == root_id:
            continue
        if not include_imports and not iri.startswith(namespace_prefix):
            continue
        record = normalize_record(obj, namespace_prefix=namespace_prefix, root_id=root_id)
        score = _score_record(record, query)
        if score <= 0:
            continue
        record["match_score"] = score
        results.append(record)

    results.sort(key=lambda item: (-int(item["match_score"]), item.get("label") or item.get("iri") or ""))
    return results[:max_items]


def get_term(
    data: list[dict[str, Any]],
    *,
    term: str,
    namespace_prefix: str,
    root_id: str,
    include_imports: bool = False,
) -> dict[str, Any] | None:
    raw = term.strip()
    if not raw:
        return None

    exact_iri = raw
    if raw.startswith("smn:") or raw.startswith("gcdfo:"):
        exact_iri = f"{namespace_prefix}{raw.split(':', 1)[1]}"
    elif not raw.startswith(("http://", "https://")):
        exact_iri = f"{namespace_prefix}{raw}"

    for obj in data:
        iri = str(obj.get("@id", ""))
        if iri == exact_iri:
            if include_imports or iri.startswith(namespace_prefix) or iri == root_id:
                return normalize_record(obj, namespace_prefix=namespace_prefix, root_id=root_id)

    raw_lower = raw.lower()
    for obj in data:
        iri = str(obj.get("@id", ""))
        if not include_imports and not (iri.startswith(namespace_prefix) or iri == root_id):
            continue
        record = normalize_record(obj, namespace_prefix=namespace_prefix, root_id=root_id)
        labels = [record.get("label") or "", record.get("pref_label") or "", record.get("local_name") or ""]
        labels.extend(record.get("alt_labels") or [])
        if any(raw_lower == item.lower() for item in labels if item):
            return record
    return None
