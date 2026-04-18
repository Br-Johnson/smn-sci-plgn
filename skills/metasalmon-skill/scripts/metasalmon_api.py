from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, load_input, result_error, write_raw


R_RUNNER = r"""
suppressWarnings({
  suppressPackageStartupMessages(library(jsonlite))
})

payload_path <- commandArgs(trailingOnly = TRUE)[1]
payload <- jsonlite::fromJSON(payload_path, simplifyVector = FALSE)

emit <- function(x) {
  cat(jsonlite::toJSON(x, auto_unbox = TRUE, null = "null", dataframe = "rows", pretty = TRUE))
}

coalesce_value <- function(x, default) {
  if (is.null(x)) return(default)
  x
}

runtime_info <- list(
  r_version = R.version.string,
  package_installed = requireNamespace("metasalmon", quietly = TRUE),
  package_version = if (requireNamespace("metasalmon", quietly = TRUE)) {
    as.character(utils::packageVersion("metasalmon"))
  } else {
    NULL
  }
)

action <- if (is.null(payload$action)) "runtime" else as.character(payload$action)

if (identical(action, "runtime")) {
  emit(list(ok = TRUE, action = action, runtime = runtime_info))
  quit(save = "no")
}

if (!runtime_info$package_installed) {
  emit(list(
    ok = FALSE,
    error = list(
      code = "missing_package",
      message = "metasalmon is not installed in the active R library"
    ),
    runtime = runtime_info,
    install_hint = "Install dfo-pacific-science/metasalmon in the active R environment before using this skill."
  ))
  quit(save = "no")
}

catalog <- list(
  search = c("sources_for_role", "find_terms", "fetch_salmon_ontology"),
  package = I(list(c("validate_salmon_datapackage"))),
  future = c("create_sdp", "read_salmon_datapackage", "render_ontology_term_request", "submit_term_request_issues")
)

safe_dataframe <- function(x) {
  if (is.null(x)) return(NULL)
  if (inherits(x, "data.frame")) return(as.data.frame(x))
  x
}

run_action <- function() {
  if (identical(action, "catalog")) {
    return(list(
      ok = TRUE,
      action = action,
      runtime = runtime_info,
      catalog = catalog,
      exports = sort(getNamespaceExports("metasalmon"))
    ))
  }

  if (identical(action, "sources_for_role")) {
    role <- if (is.null(payload$role)) NA_character_ else as.character(payload$role)
    return(list(
      ok = TRUE,
      action = action,
      role = role,
      runtime = runtime_info,
      sources = unname(metasalmon::sources_for_role(role))
    ))
  }

  if (identical(action, "find_terms")) {
    if (is.null(payload$query) || !nzchar(as.character(payload$query))) {
      stop("find_terms requires query")
    }
    role <- if (is.null(payload$role)) NA_character_ else as.character(payload$role)
    sources <- if (is.null(payload$sources)) {
      c("smn", "gcdfo", "ols", "nvs")
    } else {
      as.character(unlist(payload$sources))
    }
    expand_query <- if (is.null(payload$expand_query)) TRUE else isTRUE(payload$expand_query)
    max_items <- if (is.null(payload$max_items)) 10L else as.integer(payload$max_items)
    result <- metasalmon::find_terms(
      query = as.character(payload$query),
      role = role,
      sources = sources,
      expand_query = expand_query
    )
    diagnostics <- attr(result, "diagnostics")
    df <- as.data.frame(result)
    if (nrow(df) > max_items) {
      df <- df[seq_len(max_items), , drop = FALSE]
    }
    return(list(
      ok = TRUE,
      action = action,
      query = as.character(payload$query),
      role = role,
      runtime = runtime_info,
      source_set = sources,
      count = nrow(df),
      results = safe_dataframe(df),
      diagnostics = safe_dataframe(diagnostics)
    ))
  }

  if (identical(action, "fetch_salmon_ontology")) {
    url <- if (is.null(payload$url)) "https://w3id.org/smn/" else as.character(payload$url)
    cached_path <- metasalmon::fetch_salmon_ontology(url = url)
    info <- file.info(cached_path)
    return(list(
      ok = TRUE,
      action = action,
      runtime = runtime_info,
      url = url,
      cached_path = cached_path,
      size_bytes = unname(info$size[[1]]),
      modified = as.character(info$mtime[[1]])
    ))
  }

  if (identical(action, "validate_salmon_datapackage")) {
    if (is.null(payload$path) || !nzchar(as.character(payload$path))) {
      stop("validate_salmon_datapackage requires path")
    }
    require_iris <- if (is.null(payload$require_iris)) FALSE else isTRUE(payload$require_iris)
    result <- metasalmon::validate_salmon_datapackage(
      path = as.character(payload$path),
      require_iris = require_iris
    )
    issues <- safe_dataframe(result$issues)
    issue_count <- if (is.null(issues)) 0 else nrow(issues)
    return(list(
      ok = identical(issue_count, 0L),
      action = action,
      runtime = runtime_info,
      path = as.character(payload$path),
      require_iris = require_iris,
      issue_count = issue_count,
      issues = issues,
      semantic_validation = safe_dataframe(result$semantic_validation)
    ))
  }

  stop("action must be one of runtime, catalog, sources_for_role, find_terms, fetch_salmon_ontology, validate_salmon_datapackage")
}

out <- tryCatch(
  run_action(),
  error = function(e) {
    list(ok = FALSE, error = list(code = "r_error", message = conditionMessage(e)), runtime = runtime_info)
  }
)

emit(out)
"""


def run_r_action(payload: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="metasalmon-skill-") as temp_dir:
        temp_root = Path(temp_dir)
        payload_path = temp_root / "payload.json"
        script_path = temp_root / "runner.R"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        script_path.write_text(R_RUNNER, encoding="utf-8")

        rscript_bin = getenv_any("RSCRIPT_BIN") or "Rscript"
        proc = subprocess.run(
            [rscript_bin, str(script_path), str(payload_path)],
            capture_output=True,
            text=True,
            check=False,
        )

    stdout = proc.stdout.strip()
    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass

    if proc.returncode != 0:
        return result_error(
            "rscript_failed",
            "Rscript execution failed",
            returncode=proc.returncode,
            stderr=proc.stderr.strip(),
            stdout=stdout,
        )

    return result_error(
        "invalid_r_output",
        "R runner did not return JSON output",
        stderr=proc.stderr.strip(),
        stdout=stdout,
    )


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:  # noqa: BLE001
        emit(result_error("invalid_input", str(exc)))
        return

    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    response = run_r_action(payload)
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
