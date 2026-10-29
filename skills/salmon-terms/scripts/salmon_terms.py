# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0",
# ]
# ///
"""salmon-terms adapter: a JSON request on stdin, metasalmonpy's answer on stdout.

Run it with uv, which reads the block above and installs metasalmonpy from its
v0.6.0 tag into a cached, isolated environment the first time:

    echo '{"action":"find_terms","query":"escapement","role":"variable"}' \
      | uv run skills/salmon-terms/scripts/salmon_terms.py

Every term in the output comes from ``metasalmonpy.find_terms()``. This script
chooses no sources, ranks nothing and filters nothing. It passes the request
through and converts the package's DataFrames to JSON. ``max_items`` only
shortens a list the package has already ordered, and ``total`` reports how many
rows the package returned.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, load_input, result_error  # noqa: E402
from _package_adapter import (  # noqa: E402
    InvalidRequest,
    captured_warnings,
    import_metasalmonpy,
    missing_package_error,
    pin_warnings,
    request_bool,
    request_positive_int,
    request_string,
    runtime_info,
    save_response,
    to_json_value,
    validate_common_request,
)

ACTIONS = ("find_terms", "sources_for_role", "runtime")
COMMON_FIELDS = {"action", "save_raw", "raw_output_path"}
REQUEST_FIELDS = {
    "find_terms": COMMON_FIELDS | {
        "query", "role", "sources", "expand_query", "max_items", "release", "snapshot_dir",
    },
    "sources_for_role": COMMON_FIELDS | {"role"},
    "runtime": COMMON_FIELDS,
}
# v0.6.0 dispatches these names but labels an unknown name a successful empty
# search. This input guard retires when the pin moves to a release that reports
# unsupported names itself. It neither chooses sources nor changes their order.
SUPPORTED_SOURCES = ("smn", "gcdfo", "ols", "nvs", "zooma", "bioportal", "qudt", "gbif", "worms")


def _role(payload: dict) -> str | None:
    """The role as the package expects it: a non-empty string, or None."""
    return request_string(payload, "role") or None


def _source_error(sources) -> dict | None:
    if sources is None:
        return None
    names = [sources] if isinstance(sources, str) else sources
    if not isinstance(names, list) or any(name is not None and not isinstance(name, str) for name in names):
        return result_error("invalid_input", "sources must be a name, an array of names, or null")
    if any(name.strip().lower() not in SUPPORTED_SOURCES for name in names if name and name.strip()):
        return result_error("unsupported_source", "sources contains an unsupported name; supported names: "
                            + ", ".join(SUPPORTED_SOURCES))
    return None


def handle_find_terms(package, payload: dict) -> dict:
    query = request_string(payload, "query", "")
    if not query:
        return result_error("missing_query", "find_terms requires query")
    max_items = request_positive_int(payload, "max_items", 10)
    role = _role(payload)
    sources = payload.get("sources")  # None lets the package use its role default
    source_error = _source_error(sources)
    if source_error is not None:
        return source_error
    expand_query = request_bool(payload, "expand_query", True)

    with captured_warnings() as caught:
        frame = package.find_terms(
            query,
            role=role,
            sources=sources,
            expand_query=expand_query,
            release=payload.get("release"),
            snapshot_dir=payload.get("snapshot_dir"),
        )
    rows = to_json_value(frame) or []
    return {
        "ok": True,
        "action": "find_terms",
        "query": query,
        "role": role,
        "sources": sources,
        "expand_query": expand_query,
        "total": len(rows),
        "count": len(rows[:max_items]),
        "results": rows[:max_items],
        "diagnostics": to_json_value(frame.attrs.get("diagnostics")),
        "ontology_release": to_json_value(frame.attrs.get("ontology_release")),
        "warnings": caught,
    }


def handle_sources_for_role(package, payload: dict) -> dict:
    role = _role(payload)
    return {
        "ok": True,
        "action": "sources_for_role",
        "role": role,
        "sources": list(package.sources_for_role(role)),
    }


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:  # noqa: BLE001
        emit(result_error("invalid_input", str(exc)))
        return
    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return
    try:
        validate_common_request(payload, "find_terms")
    except InvalidRequest as exc:
        emit(result_error("invalid_input", str(exc)))
        return

    package = import_metasalmonpy()
    if package is None:
        emit(missing_package_error(__file__))
        return
    runtime = runtime_info(package)

    action = request_string(payload, "action", "find_terms")
    try:
        fields = REQUEST_FIELDS.get(action) if isinstance(action, str) else None
        unexpected = sorted(set(payload) - fields) if fields is not None else []
        if unexpected:
            response = result_error("invalid_input", f"Unknown fields for {action}: {', '.join(unexpected)}")
        elif action == "find_terms":
            response = handle_find_terms(package, payload)
        elif action == "sources_for_role":
            response = handle_sources_for_role(package, payload)
        elif action == "runtime":
            response = {"ok": True, "action": "runtime"}
        else:
            response = result_error(
                "invalid_action", f"action must be one of {', '.join(ACTIONS)}"
            )
    except InvalidRequest as exc:
        response = result_error("invalid_input", str(exc), action=action)
    except Exception as exc:  # noqa: BLE001 - report the package's own message
        response = result_error("package_error", str(exc), action=action)

    response["runtime"] = runtime
    response["warnings"] = pin_warnings(runtime) + list(response.get("warnings", []))
    save_response(response, payload, "salmon-terms-raw.json")
    emit(response)


if __name__ == "__main__":
    main()
