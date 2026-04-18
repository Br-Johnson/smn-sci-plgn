from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, load_input, result_error, write_raw
from ontology_lookup_common import get_term, load_jsonld_document, ontology_metadata, search_terms


ROOT_ID = "https://w3id.org/smn"
NAMESPACE_PREFIX = "https://w3id.org/smn/"
CANDIDATES = [
    "https://salmon-data-mobilization.github.io/salmon-domain-ontology/smn.jsonld",
    "https://raw.githubusercontent.com/salmon-data-mobilization/salmon-domain-ontology/main/docs/smn.jsonld",
]


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:  # noqa: BLE001
        emit(result_error("invalid_input", str(exc)))
        return

    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    action = payload.get("action", "meta")
    timeout = int(payload.get("timeout_sec", 20))
    include_imports = bool(payload.get("include_imports", False))

    try:
        data, source = load_jsonld_document(
            env_value=getenv_any("SMN_ONTOLOGY_JSONLD"),
            candidates=CANDIDATES,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        emit(result_error("source_load_failed", "could not load published smn JSON-LD", details=str(exc)))
        return

    response = {
        "ok": True,
        "ontology": "smn",
        "source": source,
        "metadata": ontology_metadata(data, root_id=ROOT_ID, namespace_prefix=NAMESPACE_PREFIX),
    }

    if action == "meta":
        emit(response)
        return

    if action == "search":
        query = str(payload.get("query", "")).strip()
        if not query:
            emit(result_error("missing_query", "search requires query"))
            return
        results = search_terms(
            data,
            query=query,
            namespace_prefix=NAMESPACE_PREFIX,
            root_id=ROOT_ID,
            include_imports=include_imports,
            max_items=int(payload.get("max_items", 10)),
        )
        response.update({"action": "search", "query": query, "count": len(results), "results": results})
    elif action == "get":
        term = str(payload.get("term", "")).strip()
        if not term:
            emit(result_error("missing_term", "get requires term"))
            return
        result = get_term(
            data,
            term=term,
            namespace_prefix=NAMESPACE_PREFIX,
            root_id=ROOT_ID,
            include_imports=include_imports,
        )
        if result is None:
            emit(result_error("not_found", "term was not found in smn lookup surface", ontology="smn", term=term))
            return
        response.update({"action": "get", "term": term, "result": result})
    else:
        emit(result_error("invalid_action", "action must be one of meta, search, get"))
        return

    response["raw_output_path"] = write_raw(
        response,
        requested=bool(payload.get("save_raw")),
        raw_output_path=payload.get("raw_output_path"),
        default_name="smn-ontology-raw.json",
    )
    emit(response)


if __name__ == "__main__":
    main()
