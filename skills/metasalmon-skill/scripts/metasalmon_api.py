# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0",
# ]
# ///
"""metasalmon-skill adapter: a JSON request on stdin, metasalmonpy's answer on stdout.

Run it with uv, which reads the block above and installs metasalmonpy from its
v0.6.0 tag into a cached, isolated environment the first time:

    echo '{"action":"runtime"}' | uv run skills/metasalmon-skill/scripts/metasalmon_api.py

metasalmonpy is the Python mirror of the metasalmon R package, and the two are
kept at the same release. This script calls metasalmonpy and converts what it
returns to JSON. Package validation and ontology fetching happen inside the
package; nothing here decides what is valid. The R route is documented in
SKILL.md rather than wrapped here, so the plugin keeps one adapter path.

The three review actions serve the sdp-semantic-review skill.
`build_review_packet` and `ingest_assessments` call the package's
write_semantic_review_packet() and ingest_semantic_assessments().
`write_assessments` turns a harness's judgements into the answer file those
two functions agree on: it copies each slot's identity from the packet and the
column order from the packet's own output.columns, and it decides nothing, so
a wrong answer reaches the package's checks unchanged.

Term search moved to the salmon-terms skill on 2026-09-25.
"""

from __future__ import annotations

import contextlib
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, load_input, result_error, write_raw  # noqa: E402
from _package_adapter import (  # noqa: E402
    METASALMON_R_REF,
    captured_warnings,
    import_metasalmonpy,
    missing_package_error,
    pin_warnings,
    runtime_info,
    to_json_value,
)

ACTIONS = (
    "runtime",
    "catalog",
    "validate_salmon_datapackage",
    "fetch_salmon_ontology",
    "build_review_packet",
    "write_assessments",
    "ingest_assessments",
)
# The review actions take an `engine` field so that an R route can be added
# without renaming them. Python is the only engine today; SKILL.md documents
# the R calls instead.
ENGINES = ("python",)
# The answer-file columns a judgement may fill, which are the packet's
# harness-owned columns less the nine identity columns this script copies from
# the packet and the two provenance columns the request names once. The packet
# says which columns are harness-owned; this list only refuses a key the packet
# would not accept, so that a misspelt column cannot vanish without a word.
JUDGEMENT_COLUMNS = (
    "llm_decision",
    "llm_confidence",
    "llm_selected_candidate_index",
    "llm_selected_iri",
    "llm_rationale",
    "llm_missing_context",
    "llm_bundle_summary",
    "llm_retry_query",
    "llm_new_term_label",
    "llm_new_term_definition",
    "llm_new_term_namespace",
    "llm_error",
)
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
    path = str(payload.get("path") or "").strip()
    if not path:
        return result_error("missing_path", "validate_salmon_datapackage requires path")
    require_iris = bool(payload.get("require_iris", False))
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
    url = str(payload.get("url") or "").strip()
    if not url:
        return result_error(
            "missing_url",
            "fetch_salmon_ontology requires url; the skill's SKILL.md lists the smn "
            "and gcdfo ontology URLs",
        )
    kwargs = {"url": url, "fallback_urls": list(payload.get("fallback_urls") or [])}
    if payload.get("cache_dir"):
        kwargs["cache_dir"] = str(payload["cache_dir"])

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


# The review actions -------------------------------------------------------


class RequestError(ValueError):
    """A review request this script cannot pass on, reported as invalid_input."""


def _text(payload: dict, key: str, *, required: bool = False) -> str | None:
    value = payload.get(key)
    if value is None:
        if required:
            raise RequestError(f"{key} is required")
        return None
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"{key} must be a non-empty string")
    return value.strip()


def _text_list(payload: dict, key: str) -> list[str] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise RequestError(f"{key} must be an array of non-empty strings")
    return value


def _flag(payload: dict, key: str) -> bool:
    value = payload.get(key, False)
    if not isinstance(value, bool):
        raise RequestError(f"{key} must be true or false")
    return value


def _engine(payload: dict) -> str:
    engine = payload.get("engine", "python")
    if engine not in ENGINES:
        raise RequestError(
            "engine must be 'python'. For R, call metasalmon's write_semantic_review_packet() "
            "and ingest_semantic_assessments() as skills/sdp-semantic-review/SKILL.md shows."
        )
    return engine


def _distinct(messages: list[str]) -> list[str]:
    """Each warning once, in first-seen order: the package warns per target, so a
    source that did not answer would otherwise fill the response."""
    return list(dict.fromkeys(messages))


def _review_function(package, name: str):
    """The package's review function, or a RequestError naming the release that has it."""
    function = getattr(package, name, None)
    if function is None:
        raise RequestError(
            f"metasalmonpy {getattr(package, '__version__', '?')} has no {name}(); "
            "the review-packet contract arrived in 0.6.0. Run this script with `uv run`."
        )
    return function


def _not_covered(rows) -> dict:
    """The blank code-value slots that code_scope left out, one entry per column.

    The package lists every slot, which for a package with a few coded columns
    is already hundreds of rows. The harness only has to tell the user which
    columns were left out and how many values each has, so that is what it gets.
    """
    columns: dict[tuple, dict] = {}
    for row in rows or []:
        key = (row.get("column_name"), row.get("dictionary_role"), row.get("target_sdp_field"))
        entry = columns.setdefault(
            key,
            {"column_name": key[0], "dictionary_role": key[1], "target_sdp_field": key[2], "code_values": 0, "examples": []},
        )
        entry["code_values"] += 1
        if len(entry["examples"]) < 3:
            entry["examples"].append(row.get("code_value"))
    return {"slots": sum(entry["code_values"] for entry in columns.values()), "columns": list(columns.values())}


def build_review_packet(package, payload: dict) -> dict:
    engine = _engine(payload)
    path = _text(payload, "path", required=True)
    kwargs: dict = {"quiet": True, "overwrite": _flag(payload, "overwrite")}
    for key in ("context_files", "sources"):
        value = _text_list(payload, key)
        if value is not None:
            kwargs[key] = value
    context_text = payload.get("context_text")
    if context_text is not None:
        if isinstance(context_text, str):
            context_text = [context_text]
        kwargs["context_text"] = _text_list({"context_text": context_text}, "context_text")
    top_n = payload.get("top_n")
    if top_n is not None:
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
            raise RequestError("top_n must be a positive whole number")
        kwargs["top_n"] = top_n
    code_scope = _text(payload, "code_scope")
    if code_scope is not None:
        kwargs["code_scope"] = code_scope
    write_packet = _review_function(package, "write_semantic_review_packet")

    # quiet=True keeps the package's summary off stdout, which carries this
    # script's one JSON answer; anything else it prints goes to stderr.
    with captured_warnings() as caught, contextlib.redirect_stdout(sys.stderr):
        result = write_packet(path, **kwargs)
    packet_path = Path(result["path"])
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    return {
        "ok": True,
        "action": "build_review_packet",
        "engine": engine,
        "path": path,
        "packet_path": str(packet_path),
        "packet_id": result["packet_id"],
        "pass": result["pass"],
        "units": result["units"],
        "targets": result["targets"],
        "answer_file": str(packet_path.parent / Path(packet["output"]["file"]).name),
        "not_covered": _not_covered(to_json_value(result.get("not_covered"))),
        "warnings": _distinct(caught),
    }


def _cell(value, where: str) -> str:
    """One answer-file cell: text as given, a number as Python writes it, null empty."""
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise RequestError(f"{where} must be a string, a number or null")
    return str(value)


def write_assessments(payload: dict) -> dict:
    """Write a harness's judgements as the packet's answer file and its sidecar.

    Each judgement names its slot by the unit's `unit_key` and the slot's
    `dictionary_role`, and fills only the answer columns in JUDGEMENT_COLUMNS.
    The nine identity columns are copied from the packet, `llm_provider` and
    `llm_model` come from the request, and the file is named and ordered as the
    packet's output member says. Slots with no judgement are left out and
    listed in `unanswered`; at pass 1 the package records each as an error
    row. A pass-2 packet is judged only where a slot says `reassess`: the
    package keeps every other slot's pass-1 answer and ignores a row for it, so
    a judgement there is refused rather than written to be dropped.
    """
    packet_path = Path(_text(payload, "packet", required=True))
    provider = _text(payload, "provider", required=True)
    model = _text(payload, "model", required=True)
    judgements = payload.get("judgements")
    if not isinstance(judgements, list) or not all(isinstance(item, dict) for item in judgements):
        raise RequestError("judgements must be an array of objects")
    overwrite = _flag(payload, "overwrite")

    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        columns = [column["name"] for column in packet["output"]["columns"]]
        answer_name = Path(packet["output"]["file"]).name
        packet_id = packet["packet_id"]
        units = packet["units"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RequestError(f"packet {packet_path} is not a readable review packet: {exc}") from exc

    slots: dict[tuple[str, str], dict] = {}
    for unit in units:
        for slot in unit["slots"]:
            address = (unit["unit_key"], slot["dictionary_role"])
            if address in slots:
                raise RequestError(f"the packet holds two slots at unit {address[0]!r}, role {address[1]!r}")
            slots[address] = slot
    # At pass 2 only a slot that gained candidates is judged again.
    settled = {address for address, slot in slots.items() if slot.get("reassess") is False}

    answers: dict[tuple[str, str], dict] = {}
    for number, judgement in enumerate(judgements, start=1):
        where = f"judgement {number}"
        address = (judgement.get("unit_key"), judgement.get("dictionary_role"))
        if address not in slots:
            raise RequestError(
                f"{where} names unit_key {address[0]!r} and dictionary_role {address[1]!r}, "
                "which address no slot in this packet"
            )
        if address in answers:
            raise RequestError(f"{where} answers a slot an earlier judgement already answered: {address}")
        if address in settled:
            raise RequestError(
                f"{where} answers {address}, which keeps its pass-1 answer because its reassess is false. "
                "At pass 2 judge only the slots marked reassess: true."
            )
        unknown = sorted(set(judgement) - {"unit_key", "dictionary_role", *JUDGEMENT_COLUMNS})
        if unknown:
            raise RequestError(
                f"{where} has fields no harness may write: {unknown}. "
                f"A judgement fills only {', '.join(JUDGEMENT_COLUMNS)}."
            )
        row = dict.fromkeys(columns, "")
        for name, value in slots[address]["identity"].items():
            row[name] = _cell(value, f"identity {name}")
        row["llm_provider"] = provider
        row["llm_model"] = model
        for name in JUDGEMENT_COLUMNS:
            if name in judgement:
                row[name] = _cell(judgement[name], f"{where} {name}")
        answers[address] = row

    answer_path = packet_path.parent / answer_name
    sidecar_path = Path(f"{answer_path}.packet-id")
    if answer_path.exists() and not overwrite:
        raise RequestError(f"{answer_path} already exists; pass overwrite: true to replace it")
    with answer_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for address in slots:  # the packet's order
            if address in answers:
                writer.writerow(answers[address])
    sidecar_path.write_text(packet_id + "\n", encoding="utf-8")
    return {
        "ok": True,
        "action": "write_assessments",
        "packet_path": str(packet_path),
        "packet_id": packet_id,
        "pass": packet.get("pass"),
        "answer_file": str(answer_path),
        "sidecar_file": str(sidecar_path),
        "rows": len(answers),
        "unanswered": [
            {"unit_key": unit_key, "dictionary_role": role}
            for unit_key, role in slots
            if (unit_key, role) not in answers and (unit_key, role) not in settled
        ],
    }


# The record columns the ingest response repeats for each target. The full
# record stays in review/semantic-llm-assessments.csv.
DECISION_COLUMNS = (
    "table_id",
    "column_name",
    "code_value",
    "dictionary_role",
    "target_sdp_field",
    "llm_decision",
    "llm_selected_candidate_index",
    "llm_selected_iri",
    "llm_escalated_from",
    "llm_error",
)


def ingest_assessments(package, payload: dict) -> dict:
    engine = _engine(payload)
    path = _text(payload, "path", required=True)
    kwargs: dict = {"quiet": True}
    for key in ("assessments", "packet", "packet_id", "provider", "model"):
        value = _text(payload, key)
        if value is not None:
            kwargs[key] = value
    ingest = _review_function(package, "ingest_semantic_assessments")
    refusal = getattr(package, "SemanticReviewError", None)
    base = {"action": "ingest_assessments", "engine": engine, "path": path}

    caught: list[str] = []
    try:
        with captured_warnings() as caught, contextlib.redirect_stdout(sys.stderr):
            result = ingest(path, **kwargs)
    except Exception as exc:  # noqa: BLE001 - a file-level refusal is an answer, not a crash
        if refusal is None or not isinstance(exc, refusal):
            raise
        # The package refuses a whole file (wrong packet, bad header, unknown
        # target, ...) with a stable code and writes nothing.
        failure = result_error("ingest_refused", str(exc), **base)
        failure["refusal_code"] = getattr(exc, "code", None)
        failure["warnings"] = _distinct(caught)
        return failure

    record = result["assessments"]
    decisions = to_json_value(record[[name for name in DECISION_COLUMNS if name in record.columns]])
    next_packet = result.get("next_packet")
    return {
        "ok": True,
        **base,
        "status": result["status"],
        "pass": result["pass"],
        "packet_id": result["packet_id"],
        "next_packet": None if next_packet is None else str(next_packet),
        "summary": to_json_value(result.get("summary")),
        "decisions": decisions,
        "findings": to_json_value(result.get("findings")),
        "record_file": str(Path(path) / "review" / "semantic-llm-assessments.csv"),
        "warnings": _distinct(caught),
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

    action = payload.get("action", "runtime")
    try:
        if action == "runtime":
            response = {"ok": True, "action": "runtime", "r_alternative": r_alternative()}
        elif action == "catalog":
            response = catalog(package)
        elif action == "validate_salmon_datapackage":
            response = validate(package, payload)
        elif action == "fetch_salmon_ontology":
            response = fetch_ontology(package, payload)
        elif action == "build_review_packet":
            response = build_review_packet(package, payload)
        elif action == "write_assessments":
            response = write_assessments(payload)
        elif action == "ingest_assessments":
            response = ingest_assessments(package, payload)
        elif action in MOVED_ACTIONS:
            response = result_error(
                "moved_action",
                f"{action} moved to the salmon-terms skill (skills/salmon-terms)",
            )
        else:
            response = result_error(
                "invalid_action", f"action must be one of {', '.join(ACTIONS)}"
            )
    except RequestError as exc:
        response = result_error("invalid_input", str(exc), action=action)
    except Exception as exc:  # noqa: BLE001 - report the package's own message
        response = result_error("package_error", str(exc), action=action)

    response["runtime"] = runtime
    response["warnings"] = pin_warnings(runtime) + list(response.get("warnings", []))
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
