# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0",
# ]
# ///
"""Adapter: marshal one JSON request to metasalmonpy ``find_terms()`` or ``sources_for_role()``.

This script holds no ranking, parsing, or ontology logic of its own. It reads
one JSON object from stdin, calls the pinned metasalmonpy release, and writes
one JSON object to stdout. Run it with ``uv run`` so the inline script
metadata above resolves the pinned dependency:

    echo '{"action":"find_terms","query":"escapement","role":"variable"}' \
      | uv run skills/salmon-terms/scripts/salmon_terms.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, load_input, result_error, write_raw

PINNED_METASALMONPY = "0.5.0"
ACTIONS = ("runtime", "sources_for_role", "find_terms")
SCRIPT_REL = "skills/salmon-terms/scripts/salmon_terms.py"


def import_engine():
    try:
        import metasalmonpy  # noqa: PLC0415
    except ImportError as exc:
        return None, result_error(
            "missing_package",
            "metasalmonpy is not importable; run this script with `uv run` so the pinned dependency resolves",
            install_hint=f"uv run {SCRIPT_REL}",
            pinned_version=PINNED_METASALMONPY,
            details=str(exc),
        )
    return metasalmonpy, None


def runtime_info(engine) -> dict:
    version = getattr(engine, "__version__", None)
    return {
        "python_version": sys.version.split()[0],
        "metasalmonpy_version": version,
        "pinned_version": PINNED_METASALMONPY,
        "pin_matches": version == PINNED_METASALMONPY,
    }


def frame_records(frame, max_items: int | None = None) -> list:
    if frame is None:
        return []
    rows = frame.head(max_items) if max_items else frame
    return json.loads(rows.to_json(orient="records"))


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:  # noqa: BLE001
        emit(result_error("invalid_input", str(exc)))
        return
    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    action = str(payload.get("action", "find_terms"))
    if action not in ACTIONS:
        emit(result_error("invalid_action", f"action must be one of {', '.join(ACTIONS)}"))
        return

    engine, error = import_engine()
    if error:
        emit(error)
        return

    runtime = runtime_info(engine)
    response: dict = {"ok": True, "action": action, "runtime": runtime}

    try:
        if action == "runtime":
            pass
        elif action == "sources_for_role":
            role = payload.get("role")
            response.update({"role": role, "sources": list(engine.sources_for_role(role))})
        else:
            query = str(payload.get("query", "")).strip()
            if not query:
                emit(result_error("missing_query", "find_terms requires query"))
                return
            role = payload.get("role")
            sources = payload.get("sources")
            max_items = int(payload.get("max_items", 10))
            frame = engine.find_terms(
                query=query,
                role=role,
                sources=list(sources) if sources else None,
                expand_query=bool(payload.get("expand_query", True)),
            )
            response.update(
                {
                    "query": query,
                    "role": role,
                    "sources_requested": list(sources) if sources else None,
                    "sources_default": list(engine.sources_for_role(role)) if not sources else None,
                    "count_total": int(len(frame)),
                    "count": int(min(len(frame), max_items)),
                    "results": frame_records(frame, max_items),
                    "diagnostics": frame_records(getattr(frame, "attrs", {}).get("diagnostics")),
                }
            )
    except Exception as exc:  # noqa: BLE001
        emit(result_error("engine_error", str(exc), action=action, runtime=runtime))
        return

    response["raw_output_path"] = write_raw(
        response,
        requested=bool(payload.get("save_raw")),
        raw_output_path=payload.get("raw_output_path"),
        default_name="salmon-terms-raw.json",
    )
    emit(response)


if __name__ == "__main__":
    main()
