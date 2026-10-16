# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0",
# ]
# ///
"""metasalmon-skill adapter: a JSON request on stdin, metasalmonpy's answer on stdout.

Run it with uv, which reads the block above and installs metasalmonpy from its
v0.5.0 tag into a cached, isolated environment the first time:

    echo '{"action":"runtime"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py

metasalmonpy is the Python mirror of the metasalmon R package, and the two are
kept at the same release. This script calls metasalmonpy and converts what it
returns to JSON. Package validation and ontology fetching happen inside the
package; nothing here decides what is valid. The R route is documented in
SKILL.md rather than wrapped here, so the plugin keeps one adapter path.

Term search moved to the salmon-terms skill on 2026-09-25.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, load_input, result_error  # noqa: E402
from _package_adapter import (  # noqa: E402
    InvalidRequest,
    METASALMON_R_REF,
    captured_warnings,
    import_metasalmonpy,
    missing_package_error,
    pin_warnings,
    request_bool,
    request_string,
    request_string_list,
    runtime_info,
    save_response,
    to_json_value,
    validate_common_request,
)

ACTIONS = ("runtime", "catalog", "validate_salmon_datapackage", "fetch_salmon_ontology")
# Actions this skill used to offer. A caller that still sends one gets a pointer
# to salmon-terms rather than a bare "invalid action". Retires at the plugin's
# next minor release, when no instruction written before 2026-09-25 should
# still be sending them.
MOVED_ACTIONS = ("find_terms", "sources_for_role")


def r_alternative() -> dict:
    """Whether this machine can take the documented R route, and at what version."""
    rscript = getenv_any("RSCRIPT_BIN") or shutil.which("Rscript")
    info = {"pinned_ref": METASALMON_R_REF, "rscript": rscript, "metasalmon_version": None}
    if not rscript:
        return info
    try:
        proc = subprocess.run(
            [
                rscript,
                "--vanilla",
                "-e",
                "if (requireNamespace('metasalmon', quietly = TRUE)) "
                "cat(as.character(utils::packageVersion('metasalmon')))",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["error"] = str(exc)
        return info
    info["metasalmon_version"] = proc.stdout.strip() or None
    return info


def catalog(package) -> dict:
    return {
        "ok": True,
        "action": "catalog",
        "actions": list(ACTIONS),
        "term_search": "skills/salmon-terms (find_terms, sources_for_role)",
        "exports": sorted(getattr(package, "__all__", [])),
    }


def validate(package, payload: dict) -> dict:
    path = request_string(payload, "path")
    if not path:
        return result_error("missing_path", "validate_salmon_datapackage requires path")
    require_iris = request_bool(payload, "require_iris", False)
    base = {"action": "validate_salmon_datapackage", "path": path, "require_iris": require_iris}

    caught: list[str] = []
    try:
        with captured_warnings() as caught:
            result = package.validate_salmon_datapackage(path, require_iris=require_iris)
    except ValueError as exc:
        # The package raises one ValueError for every failed check. For
        # structural failures the typed issue table rides on the exception.
        failure = result_error("validation_failed", str(exc), **base)
        failure["issues"] = to_json_value(getattr(exc, "issues", None))
        failure["warnings"] = caught
        return failure

    issues = to_json_value(result.get("issues")) or []
    return {
        "ok": True,
        **base,
        "issue_count": len(issues),
        "issues": issues,
        "semantic_validation": to_json_value(result.get("semantic_validation")),
        "warnings": caught,
    }


def fetch_ontology(package, payload: dict) -> dict:
    # No default URL on purpose. metasalmon defaults to smn and metasalmonpy to
    # gcdfo, and each package's default fallback URL is for its own default
    # ontology, so an unqualified call could quietly return a different
    # ontology from the one asked for. The caller names the URL, and nothing is
    # tried after it unless the caller also names fallback URLs.
    url = request_string(payload, "url")
    if not url:
        return result_error(
            "missing_url",
            "fetch_salmon_ontology requires url; the skill's SKILL.md lists the smn "
            "and gcdfo ontology URLs",
        )
    kwargs = {"url": url, "fallback_urls": request_string_list(payload, "fallback_urls") or []}
    cache_dir = request_string(payload, "cache_dir")
    if cache_dir:
        kwargs["cache_dir"] = cache_dir

    with captured_warnings() as caught:
        cached_path = package.fetch_salmon_ontology(**kwargs)
    stat = Path(cached_path).stat()
    return {
        "ok": True,
        "action": "fetch_salmon_ontology",
        "url": url,
        "fallback_urls": kwargs["fallback_urls"],
        "cached_path": cached_path,
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "warnings": caught,
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
        validate_common_request(payload, "runtime")
    except InvalidRequest as exc:
        emit(result_error("invalid_input", str(exc)))
        return

    package = import_metasalmonpy()
    if package is None:
        emit(missing_package_error(__file__))
        return
    runtime = runtime_info(package)

    action = request_string(payload, "action", "runtime")
    try:
        if action == "runtime":
            response = {"ok": True, "action": "runtime", "r_alternative": r_alternative()}
        elif action == "catalog":
            response = catalog(package)
        elif action == "validate_salmon_datapackage":
            response = validate(package, payload)
        elif action == "fetch_salmon_ontology":
            response = fetch_ontology(package, payload)
        elif action in MOVED_ACTIONS:
            response = result_error(
                "moved_action",
                f"{action} moved to the salmon-terms skill (skills/salmon-terms)",
            )
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
    save_response(response, payload, "metasalmon-raw.json")
    emit(response)


if __name__ == "__main__":
    main()
