# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0",
# ]
# ///
"""salmon-terms adapter: a JSON request on stdin, metasalmonpy's answer on stdout.

Run it with uv, which reads the block above and installs metasalmonpy from its
v0.5.0 tag into a cached, isolated environment the first time:

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

from _common import emit, load_input, result_error, write_raw  # noqa: E402
from _package_adapter import (  # noqa: E402
    captured_warnings,
    import_metasalmonpy,
    missing_package_error,
    pin_warnings,
    runtime_info,
    to_json_value,
)

ACTIONS = ("find_terms", "sources_for_role", "runtime")


def _role(payload: dict) -> str | None:
    """The role as the package expects it: a non-empty string, or None."""
    role = payload.get("role")
    if role is None or str(role).strip() == "":
        return None
    return str(role).strip()


def handle_find_terms(package, payload: dict) -> dict:
    query = str(payload.get("query", "")).strip()
    if not query:
        return result_error("missing_query", "find_terms requires query")
    try:
        max_items = int(payload.get("max_items", 10))
    except (TypeError, ValueError):
        return result_error("invalid_input", "max_items must be an integer")
    role = _role(payload)
    sources = payload.get("sources")  # None lets the package use its role default
    expand_query = bool(payload.get("expand_query", True))

    with captured_warnings() as caught:
        frame = package.find_terms(
            query,
            role=role,
            sources=sources,
            expand_query=expand_query,
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

    package = import_metasalmonpy()
    if package is None:
        emit(missing_package_error(__file__))
        return
    runtime = runtime_info(package)

    action = payload.get("action", "find_terms")
    try:
        if action == "find_terms":
            response = handle_find_terms(package, payload)
        elif action == "sources_for_role":
            response = handle_sources_for_role(package, payload)
        elif action == "runtime":
            response = {"ok": True, "action": "runtime"}
        else:
            response = result_error(
                "invalid_action", f"action must be one of {', '.join(ACTIONS)}"
            )
    except Exception as exc:  # noqa: BLE001 - report the package's own message
        response = result_error("package_error", str(exc), action=action)

    response["runtime"] = runtime
    response["warnings"] = pin_warnings(runtime) + list(response.get("warnings", []))
    if response.get("ok"):
        response["raw_output_path"] = write_raw(
            response,
            requested=bool(payload.get("save_raw")),
            raw_output_path=payload.get("raw_output_path"),
            default_name="salmon-terms-raw.json",
        )
    emit(response)


if __name__ == "__main__":
    main()
