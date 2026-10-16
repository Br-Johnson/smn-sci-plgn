# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0",
# ]
# ///
"""Replay harness answers through metasalmonpy and score them on the Theme A oracles.

The deterministic half of the sdp-semantic-review skill's eval. Each Theme A
case in ``theme-a/cases-v1.json`` states the semantic outcome a correct review
reaches: events that must be observed (``required``), may be (``allowed_not_required``)
and must not be (``forbidden``). This script turns a harness's answer file into
those events with the pinned package, through its public functions only, and
scores them:

1. ``write_semantic_review_packet()`` rebuilds the case's packet from the
   vendored ``input.json``, and its ``packet_id`` must equal the vendored
   ``packet-1.json``'s, so the pinned release writes the contract the fixtures pin.
2. ``ingest_semantic_assessments()`` reads the answer file. A retry is replayed
   as a search that finds nothing new, because the replay is offline.
3. The events are read from what the package produced: one assessment and, when
   a candidate is chosen, one selection per target; a prefill for each slot that
   ``apply_semantic_suggestions(strategy="llm")`` fills; a gap for each row of
   ``detect_semantic_term_gaps()``; a routing for each smn, gcdfo or profile
   request ``render_ontology_term_request()`` drafts.

``controls`` runs the checks that say the instrument works: the vendored files
match the manifest; every conformance case's recorded answer reproduces the
events the package recorded for it (``expected/events.json``); the six Theme A
answers and the three adversarial variants pass their oracles; and a wrong
answer fails one. ``cohort`` scores recorded skill runs (``cohort/cohort.json``)
and fails when any blocking case fails.

Usage, from the repository root:

    uv run -q evals/sdp-semantic-review/replay_theme_a.py controls
    uv run -q evals/sdp-semantic-review/replay_theme_a.py cohort

The oracle evaluation mirrors ``evaluate_oracles()`` in metasalmon's
``scripts/theme-a-benchmark.R``, and the event builder mirrors its
``events_from_package_outputs()``; the controls are what keep them honest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
THEME_A = HERE / "theme-a"
FIXTURES = THEME_A / "v1"
COHORT = HERE / "cohort"

# The conformance case that carries each Theme A case's recorded answer, as
# metasalmon's tests/testthat/helper-semantic-review.R maps them.
FIXTURE_CASE = {
    "catch_count": "ta_catch_count",
    "catch_weight_advisory": "ta_catch_weight",
    "fork_length_explicit_procedure": "ta_fork_length",
    "ocean_phase_explicit_lifecycle": "ta_ocean_phase",
    "synthetic_structured_gap": "ta_gap",
    "handcrafted_gcdfo_routing": "ta_gcdfo_routing",
}
# Adversarial answers, each scored on the Theme A case it varies. The package's
# validators or its escalation must still bring each one to a pass.
ADVERSARIAL_CASE = {
    "ta_method_accept": "catch_count",
    "ta_ctx_accept": "catch_count",
    "ta_gap_reject": "synthetic_structured_gap",
}
VENDORED_FILES = ("input.json", "packet-1.json", "harness-1.csv", "harness-1.csv.packet-id", "expected/events.json")
AUTO_APPLY_ROLES = ["variable", "property", "entity", "unit"]
PREFILL_FIELDS = {"variable": "term_iri", "property": "property_iri", "entity": "entity_iri", "unit": "unit_iri"}
REQUEST_SCOPES = ("smn", "gcdfo", "profile")
ORACLE_IGNORED_FIELDS = {"rule_id", "note", "advisory"}


# -- Oracle evaluation (no package needed) -------------------------------------


def scalar_key(value) -> str:
    """One comparable text per value, as theme-a-benchmark.R's scalar_key()."""
    if value is None:
        return "<NA>"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and math.isnan(value):
        return "<NA>"
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def event_matches_rule(event: dict, rule: dict) -> bool:
    return all(
        field in event and scalar_key(event[field]) == scalar_key(rule[field])
        for field in rule
        if field not in ORACLE_IGNORED_FIELDS
    )


def evaluate_case(case: dict, events: list[dict]) -> list[dict]:
    """The failures of one case's oracle against observed events."""
    failures = []
    for rule in case["oracle"].get("required", []):
        if rule.get("advisory"):
            continue
        if not any(event_matches_rule(event, rule) for event in events):
            failures.append({"case_id": case["case_id"], "bucket": "required", "rule_id": rule["rule_id"],
                             "message": "Required semantic event was not observed."})
    for rule in case["oracle"].get("forbidden", []):
        if any(event_matches_rule(event, rule) for event in events):
            failures.append({"case_id": case["case_id"], "bucket": "forbidden", "rule_id": rule["rule_id"],
                             "message": "Forbidden semantic event was observed."})
    return failures


def evaluate(cases: list[dict], observed: dict[str, list[dict]]) -> dict:
    """Score observed events, keyed by case_id, on each case's oracle.

    A case with no observed events is scored on an empty list, so every
    required rule fails rather than the case being skipped.
    """
    failures = []
    results = []
    for case in cases:
        case_failures = evaluate_case(case, observed.get(case["case_id"], []))
        failures.extend(dict(failure, blocking=bool(case.get("blocking"))) for failure in case_failures)
        results.append({"case_id": case["case_id"], "blocking": bool(case.get("blocking")), "passed": not case_failures})
    blocking = [failure for failure in failures if failure["blocking"]]
    return {"status": "fail" if blocking else "pass", "cases": results, "failures": failures}


def load_cases() -> list[dict]:
    return json.loads((THEME_A / "cases-v1.json").read_text(encoding="utf-8"))["cases"]


# -- Replay through the package ----------------------------------------------


def _present(value) -> bool:
    if value is None:
        return False
    try:
        import pandas as pd

        if value is pd.NA:
            return False
    except ImportError:  # pragma: no cover - the package brings pandas
        pass
    if isinstance(value, float) and math.isnan(value):
        return False
    return bool(str(value).strip())


def _frame(rows: list[dict], numeric=(), integer=(), logical=()):
    import pandas as pd

    if not rows:
        return pd.DataFrame()
    data = {}
    for column in dict.fromkeys(key for row in rows for key in row):
        values = [row.get(column) for row in rows]
        if column in numeric:
            data[column] = pd.Series([math.nan if v is None else float(v) for v in values], dtype="float64")
        elif column in integer:
            data[column] = pd.Series([pd.NA if v is None else int(v) for v in values], dtype="Int64")
        elif column in logical:
            data[column] = pd.Series([None if v is None else bool(v) for v in values], dtype="object")
        else:
            data[column] = pd.Series([None if v is None else str(v) for v in values], dtype="object")
    return pd.DataFrame(data)


def case_dictionary(case_input: dict):
    """The in-memory dictionary a conformance case's input.json describes."""
    dictionary = _frame(case_input["dictionary"])
    dictionary.attrs["semantic_targets"] = _frame(case_input["targets"])
    dictionary.attrs["semantic_suggestions"] = _frame(
        case_input["candidates"],
        numeric=("score", "role_hint_bonus"),
        integer=("retrieval_pass",),
        logical=("alignment_only", "role_collision"),
    )
    return dictionary


def _nothing_found(*_args, **_kwargs):
    import pandas as pd

    return pd.DataFrame()


def events_from_outputs(assessments, before, after, gaps, requests) -> list[dict]:
    events = []
    for _, row in assessments.iterrows():
        decision = str(row["llm_decision"]) if _present(row["llm_decision"]) else None
        events.append({"type": "assessment", "role": row["dictionary_role"], "decision": decision})
        if _present(row["llm_selected_iri"]):
            events.append({"type": "selection", "role": row["dictionary_role"],
                           "iri": str(row["llm_selected_iri"]), "decision": decision})
    for position in range(len(after)):
        for role, field in PREFILL_FIELDS.items():
            if field not in after.columns:
                continue
            new = after.iloc[position][field]
            old = before.iloc[position][field] if field in before.columns else None
            if _present(new) and not _present(old):
                events.append({"type": "prefill", "role": role, "iri": str(new), "decision": "accept"})
    for _, gap in gaps.iterrows():
        if "llm_decision" in gaps.columns and _present(gap["llm_decision"]):
            decision = str(gap["llm_decision"])
        elif "detection" in gaps.columns and _present(gap["detection"]):
            decision = str(gap["detection"])
        else:
            decision = "candidate_gap"
        scope = "uncertain"
        if "llm_new_term_namespace" in gaps.columns and _present(gap["llm_new_term_namespace"]):
            namespace = str(gap["llm_new_term_namespace"]).strip().lower()
            scope = namespace if namespace in REQUEST_SCOPES else "uncertain"
        if scope == "uncertain" and "placement_recommendation" in gaps.columns and _present(gap["placement_recommendation"]):
            placement = str(gap["placement_recommendation"]).strip().lower()
            scope = placement if placement in REQUEST_SCOPES else "uncertain"
        events.append({"type": "gap", "role": str(gap["dictionary_role"]), "scope": scope, "decision": decision})
    if len(requests):
        for _, request in requests[requests["request_scope"].isin(REQUEST_SCOPES)].iterrows():
            events.append({"type": "routing", "scope": str(request["request_scope"]),
                           "repository": str(request["ontology_repo"])})
    return events


def replay(fixture_case: str, answer: Path, sidecar: Path | None = None) -> dict:
    """Ingest one answer file against a conformance case and return its events.

    ``answer`` answers the case's pass-1 packet; ``sidecar`` names that packet
    and defaults to the file beside the answer.
    """
    import metasalmonpy as ms
    import pandas as pd

    case_dir = FIXTURES / fixture_case
    case_input = json.loads((case_dir / "input.json").read_text(encoding="utf-8"))
    vendored = json.loads((case_dir / "packet-1.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        review = Path(tmp) / "review"
        dictionary = case_dictionary(case_input)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            built = ms.write_semantic_review_packet(
                dictionary, context_text=case_input["context_text"], top_n=case_input.get("top_n", 5),
                review_dir=review, quiet=True,
            )
        if built["packet_id"] != vendored["packet_id"]:
            raise SystemExit(
                f"{fixture_case}: the pinned release wrote packet {built['packet_id']}, "
                f"not the vendored {vendored['packet_id']}; the fixtures and the pin disagree"
            )
        shutil.copy(answer, review / "semantic-assessments-pass-1.csv")
        shutil.copy(sidecar or Path(f"{answer}.packet-id"), review / "semantic-assessments-pass-1.csv.packet-id")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = ms.ingest_semantic_assessments(dictionary, review_dir=review, search_fn=_nothing_found, quiet=True)
            before = dictionary.copy()
            before.attrs = {}
            after = ms.apply_semantic_suggestions(
                before.copy(), suggestions=result["suggestions"], strategy="llm",
                roles=AUTO_APPLY_ROLES, overwrite=False, verbose=False,
            )
            gaps = ms.detect_semantic_term_gaps(result["dictionary"])
            requests = (
                ms.render_ontology_term_request(gaps, scope="auto", ask=False, profile_name="theme-a-benchmark")
                if len(gaps) else pd.DataFrame()
            )
    return {
        "status": result["status"],
        "findings": sorted({str(code) for code in result["findings"].get("code", [])})
        if hasattr(result["findings"], "get") else [],
        "events": events_from_outputs(result["assessments"], before, after, gaps, requests),
    }


# -- Modes -------------------------------------------------------------------


def check_manifest() -> int:
    """Every vendored fixture file is the one metasalmon's manifest names.

    The manifest is metasalmon's, unchanged, so it lists every conformance
    case. Only the files the replay reads are vendored, and each of them must
    be present and match its SHA-256.
    """
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))["files"]
    needed = {f"{case}/{name}" for case in [*FIXTURE_CASE.values(), *ADVERSARIAL_CASE] for name in VENDORED_FILES}
    present = {
        path.relative_to(FIXTURES).as_posix()
        for path in FIXTURES.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    problems = [f"{name}: missing" for name in sorted(needed - present)]
    problems += [f"{name}: not one of the files the replay reads" for name in sorted(present - needed)]
    for name in sorted(needed & present):
        if name not in manifest:
            problems.append(f"{name}: not in the manifest")
        elif hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() != manifest[name]:
            problems.append(f"{name}: SHA-256 differs from the manifest")
    if problems:
        raise SystemExit("vendored fixtures do not match the manifest:\n  " + "\n  ".join(problems))
    return len(needed)


def wrong_answer(source: Path, destination: Path) -> Path:
    """catch_count's recorded answer with the variable left for review."""
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = reader.fieldnames
    for row in rows:
        if row["dictionary_role"] == "variable":
            row.update(llm_decision="review", llm_selected_candidate_index="", llm_selected_iri="")
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    shutil.copy(Path(f"{source}.packet-id"), Path(f"{destination}.packet-id"))
    return destination


def run_controls() -> dict:
    cases = load_cases()
    by_id = {case["case_id"]: case for case in cases}
    report = {"fixture_files": check_manifest(), "reproduced": [], "oracles": None, "adversarial": {}, "negative_control": None}

    observed = {}
    for fixture_case in [*FIXTURE_CASE.values(), *ADVERSARIAL_CASE]:
        expected = json.loads((FIXTURES / fixture_case / "expected" / "events.json").read_text(encoding="utf-8"))
        run = replay(fixture_case, FIXTURES / fixture_case / "harness-1.csv")
        if run["events"] != expected["events"]:
            raise SystemExit(
                f"{fixture_case}: the replay did not reproduce the package's recorded events\n"
                f"  observed: {json.dumps(run['events'])}\n  expected: {json.dumps(expected['events'])}"
            )
        report["reproduced"].append(fixture_case)
        observed[fixture_case] = run["events"]

    theme_a = evaluate(cases, {case_id: observed[fixture] for case_id, fixture in FIXTURE_CASE.items()})
    if theme_a["status"] != "pass":
        raise SystemExit(f"the recorded Theme A answers fail their oracles: {theme_a['failures']}")
    report["oracles"] = theme_a["status"]

    for fixture_case, case_id in ADVERSARIAL_CASE.items():
        result = evaluate([by_id[case_id]], {case_id: observed[fixture_case]})
        if result["status"] != "pass":
            raise SystemExit(f"{fixture_case}: the package did not protect {case_id}: {result['failures']}")
        report["adversarial"][fixture_case] = result["status"]

    with tempfile.TemporaryDirectory() as tmp:
        answer = wrong_answer(FIXTURES / "ta_catch_count" / "harness-1.csv", Path(tmp) / "wrong.csv")
        result = evaluate([by_id["catch_count"]], {"catch_count": replay("ta_catch_count", answer)["events"]})
    if result["status"] != "fail":
        raise SystemExit("negative control: a wrong answer passed the catch_count oracle, so the evaluator cannot fail")
    report["negative_control"] = sorted(failure["rule_id"] for failure in result["failures"])
    report["status"] = "pass"  # every failed control has already exited
    return report


def guide_changes(guide: dict) -> list[str]:
    """The skill documents that no longer match the digests a cohort recorded.

    Informational: the recorded answers still replay, but a changed guide means
    they no longer show what the current guide produces.
    """
    changed = []
    for name, digest in sorted(guide.items()):
        path = ROOT / name
        current = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if current != digest:
            changed.append(name)
    return changed


def run_cohort(cohort_dir: Path = COHORT) -> dict:
    """Score every recorded run in cohort.json; any blocking failure fails."""
    cohort = json.loads((cohort_dir / "cohort.json").read_text(encoding="utf-8"))
    cases = load_cases()
    report = {"guide_changed_since_recorded": guide_changes(cohort.get("guide", {})), "runs": []}
    failed = []
    for run in cohort["runs"]:
        observed = {}
        for case in cases:
            fixture_case = FIXTURE_CASE[case["case_id"]]
            answer = cohort_dir / run["run_id"] / fixture_case / "semantic-assessments-pass-1.csv"
            if answer.exists():
                observed[case["case_id"]] = replay(fixture_case, answer)["events"]
        result = evaluate(cases, observed)
        report["runs"].append({"run_id": run["run_id"], "status": result["status"],
                               "promoted_by": run.get("promoted_by"), "failures": result["failures"]})
        if result["status"] != "pass":
            failed.append(run["run_id"])
    if not cohort["runs"]:
        raise SystemExit("cohort.json records no runs")
    report["status"] = "fail" if failed else "pass"
    return report


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "controls"
    if mode == "controls":
        report = run_controls()
    elif mode == "cohort":
        report = run_cohort(Path(argv[2]) if len(argv) > 2 else COHORT)
    else:
        print(f"unknown mode {mode!r}; use controls or cohort", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
