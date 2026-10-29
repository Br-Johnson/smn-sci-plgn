# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0",
# ]
# ///
"""Replay authored year/age/EFS role controls through the released public API.

This is a contract instrument and guide regression, not a live-model score or
scientific validator. Case expectations are hand-authored. The package creates
packets, the existing plugin adapter writes answers, and the package ingests
them. No metadata is applied, term request submitted, provider called or source
searched. The existing Theme A oracle evaluator checks the resulting events.
"""
from __future__ import annotations

import importlib.util
import importlib.metadata
import json
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE = HERE / "role-boundaries" / "cases-v1.json"
ADAPTER = ROOT / "skills" / "metasalmon-skill" / "scripts" / "metasalmon_api.py"

spec = importlib.util.spec_from_file_location("role_theme_a_oracles", HERE / "replay_theme_a.py")
THEME_A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(THEME_A)
evaluate = THEME_A.evaluate


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def dictionary_input(case: dict) -> dict:
    """Expand declared synthetic data into the existing conformance input shape."""
    role = case["role"]
    column = case["column_name"]
    dictionary = {
        "dataset_id": "role_fixture", "table_id": "synthetic", "column_name": column,
        "column_label": column, "column_description": case["description"],
        "column_role": "measurement", "value_type": "number", "unit_label": None,
        **{field: None for field in ("term_iri", "property_iri", "entity_iri", "unit_iri",
                                    "constraint_iri", "statistical_modifier_iri", "method_iri")},
        "term_type": None,
    }
    target = {
        "dataset_id": "role_fixture", "table_id": "synthetic", "column_name": column,
        "code_value": None, "dictionary_role": role, "search_role": role,
        "target_scope": "column", "target_sdp_file": "column_dictionary.csv",
        "target_sdp_field": "term_iri" if role == "variable" else role + "_iri",
        "target_row_key": f"role_fixture/synthetic/{column}", "target_label": column,
        "target_description": case["description"], "search_query": case["description"],
        "target_query_basis": "column_description", "target_query_context": case["description"],
        "column_label": column, "column_description": case["description"],
        "code_label": None, "code_description": None,
    }
    return {"dictionary": [dictionary], "targets": [target],
            "candidates": [{**target, **candidate, "role": role, "retrieval_pass": 1}
                           for candidate in case["candidates"]]}


def refuse_search(*_args, **_kwargs):
    raise AssertionError("The role fixture must not invoke vocabulary or provider services.")


def replay(case: dict, *, wrong: bool = False, check_packet_id: bool = True) -> dict:
    import metasalmonpy as ms

    dictionary = THEME_A.case_dictionary(dictionary_input(case))
    with tempfile.TemporaryDirectory(prefix="semantic-role-") as scratch:
        review = Path(scratch) / "review"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            built = ms.write_semantic_review_packet(
                dictionary, context_text=case["context_text"], search_fn=refuse_search,
                review_dir=review, quiet=True,
            )
        packet_path = review / "semantic-review-packet.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        if check_packet_id and packet["packet_id"] != case["packet_id"]:
            raise AssertionError(f"{case['case_id']}: released packet fingerprint changed")
        unit = packet["units"][0]
        slot = next(s for s in unit["slots"] if s["dictionary_role"] == case["role"])
        answer = dict(case["wrong_judgement"] if wrong else case["judgement"])
        selected = answer.get("llm_selected_iri")
        if selected:
            # The answer writer accepts only the packet's index contract. A
            # proposal-only negative control deliberately echoes an absent IRI.
            answer["llm_selected_candidate_index"] = next(
                (c["index"] for c in slot["candidates"] if c["iri"] == selected), 1
            )
        request = {
            "action": "write_assessments", "packet": str(packet_path),
            "provider": "hand-authored-fixture", "model": "no-model-run",
            "judgements": [{"unit_key": unit["unit_key"],
                            "dictionary_role": case["role"], **answer}],
        }
        proc = subprocess.run([sys.executable, str(ADAPTER)], input=json.dumps(request),
                              capture_output=True, text=True, check=True)
        written = json.loads(proc.stdout)
        if not written.get("ok") or written.get("unanswered"):
            raise AssertionError(f"{case['case_id']}: answer writer refused the fixture: {written}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = ms.ingest_semantic_assessments(
                dictionary, review_dir=review, search_fn=refuse_search, quiet=True,
            )
        events = []
        for _, row in result["assessments"].iterrows():
            decision = str(row["llm_decision"]) if THEME_A._present(row["llm_decision"]) else None
            events.append({"type": "assessment", "role": row["dictionary_role"], "decision": decision})
            if THEME_A._present(row["llm_selected_iri"]):
                events.append({"type": "selection", "role": row["dictionary_role"],
                               "iri": str(row["llm_selected_iri"]), "decision": decision})
        fields = [name for name in ("term_iri", "property_iri", "constraint_iri", "method_iri")
                  if name in result["dictionary"].columns]
        metadata = {field: [str(value) if THEME_A._present(value) else None
                            for value in result["dictionary"][field]] for field in fields}
        return {
            "metadata_values": metadata,
            "packet_id": packet["packet_id"], "status": result["status"], "events": events,
            "findings": sorted({str(code) for code in result["findings"].get("code", [])}),
            "packet_candidates": slot["candidates"],
            "ingest_errors": [str(value) for value in result["assessments"].get("llm_error", []) if THEME_A._present(value)],
            "metadata_applied": False, "model_run": False,
        }


def controls() -> dict:
    fixture = load_fixture()
    cases = fixture["cases"]
    package = importlib.metadata.distribution("metasalmonpy")
    source = json.loads(package.read_text("direct_url.json") or "{}")
    if source.get("vcs_info", {}).get("commit_id") != fixture["package"]["commit"]:
        raise AssertionError("Use the exact pinned Git release; version text alone does not identify the reviewed implementation.")
    observed = {case["case_id"]: replay(case) for case in cases}
    correct = evaluate(cases, {key: value["events"] for key, value in observed.items()})
    proposals_off_shortlists = all(
        candidate["iri"] not in fixture["proposal_only_iris"]
        for run in observed.values() for candidate in run["packet_candidates"]
    )
    wrong = {case["case_id"]: replay(case, wrong=True) for case in cases}
    wrong_scores = {case["case_id"]: evaluate([case], {case["case_id"]: wrong[case["case_id"]]["events"]})
                    for case in cases}
    raw_count = wrong_scores["efs_preserves_adjusted_variable"]
    proposal_events = wrong["proposal_not_released_shortlist"]["events"]
    proposal_refused = (not any(e.get("decision") == "accept" for e in proposal_events)
                        and bool(wrong["proposal_not_released_shortlist"]["ingest_errors"]))
    raw_count_accepted = any(e.get("type") == "selection" and e.get("decision") == "accept"
                             and e.get("iri") == "https://example.org/fixture/RawFemaleCount"
                             for e in wrong["efs_preserves_adjusted_variable"]["events"])
    return {
        "status": "pass" if correct["status"] == "pass" and raw_count["status"] == "fail" and raw_count_accepted and proposal_refused and proposals_off_shortlists else "fail",
        "fixture_kind": fixture["fixture_kind"], "package": {**fixture["package"], "installed_source": source},
        "correct_answers": correct,
        "wrong_answers": {key: {"oracle_status": wrong_scores[key]["status"],
                                "events": run["events"], "findings": run["findings"],
                                "ingest_errors": run["ingest_errors"]}
                          for key, run in wrong.items()},
        "proposal_off_shortlist_refused": proposal_refused,
        "proposal_names_absent_from_shortlists": proposals_off_shortlists,
        "limitation": "Authored decisions replay deterministically; no live harness quality or scientific approval is established.",
    }


if __name__ == "__main__":
    report = controls()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["status"] == "pass" else 1)
