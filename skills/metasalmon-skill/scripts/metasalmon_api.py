# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0",
# ]
# ///
"""Adapter: marshal one JSON request to the Salmon Data Package engine.

Python-first: the default engine is the pinned metasalmonpy release, resolved
by ``uv run`` from the inline metadata above. The R runner is an interim
engine for environments that have ``metasalmon`` installed in R; select it
with ``{"engine":"r"}`` or ``METASALMON_ENGINE=r``. Both engines expose the
same actions and the same JSON shape. This script holds no package logic.

    echo '{"action":"runtime"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, load_input, result_error, write_raw

PINNED_METASALMON = "0.5.0"
PINNED_METASALMONPY = "0.5.0"
UPSTREAM_R = "salmon-data-mobilization/metasalmon"
UPSTREAM_PY = "salmon-data-mobilization/metasalmonpy"
SCRIPT_REL = "skills/metasalmon-skill/scripts/metasalmon_api.py"
ACTIONS = ("runtime", "catalog", "fetch_salmon_ontology", "validate_salmon_datapackage")
MOVED_TO_SALMON_TERMS = ("find_terms", "sources_for_role")
FUTURE = ("create_sdp", "read_salmon_datapackage", "render_ontology_term_request", "submit_term_request_issues")


def jsonable(value):
    """Convert engine return values to JSON-safe data without interpreting them."""
    if hasattr(value, "to_json") and hasattr(value, "columns"):
        return json.loads(value.to_json(orient="records"))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


# --- Python engine -----------------------------------------------------------


def run_python(payload: dict, action: str) -> dict:
    try:
        import metasalmonpy  # noqa: PLC0415
    except ImportError as exc:
        return result_error(
            "missing_package",
            "metasalmonpy is not importable; run this script with `uv run` so the pinned dependency resolves",
            install_hint=f"uv run {SCRIPT_REL}",
            pinned_version=PINNED_METASALMONPY,
            details=str(exc),
        )

    version = getattr(metasalmonpy, "__version__", None)
    runtime = {
        "engine": "python",
        "python_version": sys.version.split()[0],
        "package": "metasalmonpy",
        "package_version": version,
        "pinned_version": PINNED_METASALMONPY,
        "pin_matches": version == PINNED_METASALMONPY,
        "upstream": UPSTREAM_PY,
    }
    response: dict = {"ok": True, "action": action, "runtime": runtime}

    try:
        if action == "runtime":
            return response
        if action == "catalog":
            response["catalog"] = catalog_block(sorted(getattr(metasalmonpy, "__all__", [])))
            return response
        if action == "fetch_salmon_ontology":
            kwargs = {key: payload[key] for key in ("url", "cache_dir") if payload.get(key)}
            cached_path = Path(metasalmonpy.fetch_salmon_ontology(**kwargs))
            stat = cached_path.stat()
            response.update(
                {
                    "url": kwargs.get("url"),
                    "cached_path": str(cached_path),
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
            return response
        path = str(payload.get("path", "")).strip()
        if not path:
            return result_error("missing_path", "validate_salmon_datapackage requires path")
        require_iris = bool(payload.get("require_iris", False))
        try:
            result = metasalmonpy.validate_salmon_datapackage(path, require_iris=require_iris)
        except Exception as exc:  # noqa: BLE001
            issues = jsonable(getattr(exc, "issues", None))
            return {
                "ok": False,
                "action": action,
                "runtime": runtime,
                "path": path,
                "require_iris": require_iris,
                "error": {"code": "validation_failed", "message": str(exc)},
                "issue_count": len(issues) if isinstance(issues, list) else None,
                "issues": issues,
            }
        response.update({"path": path, "require_iris": require_iris, "issue_count": 0, "result": jsonable(result)})
        return response
    except Exception as exc:  # noqa: BLE001
        return result_error("engine_error", str(exc), action=action, runtime=runtime)


def catalog_block(exports: list[str]) -> dict:
    return {
        "actions": list(ACTIONS),
        "moved_to_salmon_terms": list(MOVED_TO_SALMON_TERMS),
        "future": list(FUTURE),
        "exports": exports,
    }


# --- Interim R engine --------------------------------------------------------

R_RUNNER = r"""
suppressWarnings(suppressPackageStartupMessages(library(jsonlite)))
args <- commandArgs(trailingOnly = TRUE)
payload <- jsonlite::fromJSON(args[1], simplifyVector = FALSE)
pinned <- args[2]
emit <- function(x) cat(jsonlite::toJSON(x, auto_unbox = TRUE, null = "null", dataframe = "rows", pretty = TRUE))

installed <- requireNamespace("metasalmon", quietly = TRUE)
version <- if (installed) as.character(utils::packageVersion("metasalmon")) else NULL
runtime <- list(engine = "r", r_version = R.version.string, package = "metasalmon",
                package_installed = installed, package_version = version,
                pinned_version = pinned, pin_matches = identical(version, pinned))
action <- if (is.null(payload$action)) "runtime" else as.character(payload$action)

if (identical(action, "runtime")) { emit(list(ok = TRUE, action = action, runtime = runtime)); quit(save = "no") }
if (!installed) {
  emit(list(ok = FALSE, error = list(code = "missing_package", message = "metasalmon is not installed in the active R library"),
            runtime = runtime, install_hint = paste0("remotes::install_github('salmon-data-mobilization/metasalmon@v", pinned, "')")))
  quit(save = "no")
}

run_action <- function() {
  if (identical(action, "catalog")) {
    return(list(ok = TRUE, action = action, runtime = runtime, catalog = list(
      actions = c("runtime", "catalog", "fetch_salmon_ontology", "validate_salmon_datapackage"),
      moved_to_salmon_terms = c("find_terms", "sources_for_role"),
      future = c("create_sdp", "read_salmon_datapackage", "render_ontology_term_request", "submit_term_request_issues"),
      exports = sort(getNamespaceExports("metasalmon")))))
  }
  if (identical(action, "fetch_salmon_ontology")) {
    cached_path <- if (is.null(payload$url)) metasalmon::fetch_salmon_ontology() else metasalmon::fetch_salmon_ontology(url = as.character(payload$url))
    info <- file.info(cached_path)
    return(list(ok = TRUE, action = action, runtime = runtime, url = payload$url, cached_path = cached_path,
                size_bytes = unname(info$size[[1]]), modified = as.character(info$mtime[[1]])))
  }
  if (identical(action, "validate_salmon_datapackage")) {
    if (is.null(payload$path) || !nzchar(as.character(payload$path))) stop("validate_salmon_datapackage requires path")
    require_iris <- isTRUE(payload$require_iris)
    result <- metasalmon::validate_salmon_datapackage(path = as.character(payload$path), require_iris = require_iris)
    issues <- result$issues
    issue_count <- if (is.null(issues)) 0L else nrow(as.data.frame(issues))
    return(list(ok = identical(issue_count, 0L), action = action, runtime = runtime, path = as.character(payload$path),
                require_iris = require_iris, issue_count = issue_count, result = result))
  }
  stop("action must be one of runtime, catalog, fetch_salmon_ontology, validate_salmon_datapackage")
}

out <- tryCatch(run_action(), error = function(e) list(ok = FALSE, error = list(code = "r_error", message = conditionMessage(e)), runtime = runtime))
emit(out)
"""


def run_r(payload: dict, action: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="metasalmon-skill-") as temp_dir:
        temp_root = Path(temp_dir)
        payload_path = temp_root / "payload.json"
        script_path = temp_root / "runner.R"
        payload_path.write_text(json.dumps({**payload, "action": action}), encoding="utf-8")
        script_path.write_text(R_RUNNER, encoding="utf-8")
        rscript_bin = getenv_any("RSCRIPT_BIN") or "Rscript"
        try:
            proc = subprocess.run(
                [rscript_bin, str(script_path), str(payload_path), PINNED_METASALMON],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return result_error("rscript_missing", f"{rscript_bin} was not found; install R or use the python engine")

    stdout = proc.stdout.strip()
    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass
    code = "rscript_failed" if proc.returncode != 0 else "invalid_r_output"
    return result_error(code, "R runner did not return JSON output", returncode=proc.returncode, stderr=proc.stderr.strip(), stdout=stdout)


# --- Entry point -------------------------------------------------------------


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:  # noqa: BLE001
        emit(result_error("invalid_input", str(exc)))
        return
    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    action = str(payload.get("action", "runtime"))
    if action in MOVED_TO_SALMON_TERMS:
        emit(result_error("moved_to_salmon_terms", f"{action} now lives in the salmon-terms skill", skill="salmon-terms", script="skills/salmon-terms/scripts/salmon_terms.py"))
        return
    if action not in ACTIONS:
        emit(result_error("invalid_action", f"action must be one of {', '.join(ACTIONS)}"))
        return

    engine = str(payload.get("engine") or getenv_any("METASALMON_ENGINE") or "python").lower()
    if engine not in {"python", "r"}:
        emit(result_error("invalid_engine", "engine must be python or r"))
        return

    response = run_python(payload, action) if engine == "python" else run_r(payload, action)
    if response.get("ok"):
        response["raw_output_path"] = write_raw(
            response,
            requested=bool(payload.get("save_raw")),
            raw_output_path=payload.get("raw_output_path"),
            default_name="metasalmon-raw.json",
        )
    emit(response)


if __name__ == "__main__":
    main()
