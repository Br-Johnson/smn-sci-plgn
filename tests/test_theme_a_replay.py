"""Offline tests for the sdp-semantic-review skill's Theme A replay.

The replay's oracle evaluation and its fixture checks need no package, so they
are tested here against the events metasalmon recorded for each conformance
case (``expected/events.json``). The replay through the package itself, with
its controls and the recorded cohort, runs in the live tests in
test_package_adapters.py.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_replay():
    spec = importlib.util.spec_from_file_location(
        "theme_a_replay", ROOT / "evals" / "sdp-semantic-review" / "replay_theme_a.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPLAY = load_replay()
CASES = REPLAY.load_cases()
BY_ID = {case["case_id"]: case for case in CASES}


def recorded(fixture_case: str) -> list[dict]:
    path = REPLAY.FIXTURES / fixture_case / "expected" / "events.json"
    return json.loads(path.read_text(encoding="utf-8"))["events"]


def recorded_by_case() -> dict[str, list[dict]]:
    return {case_id: recorded(fixture) for case_id, fixture in REPLAY.FIXTURE_CASE.items()}


class OracleTests(unittest.TestCase):
    def test_every_theme_a_case_has_a_vendored_answer(self):
        self.assertEqual(set(REPLAY.FIXTURE_CASE), set(BY_ID))
        self.assertTrue(set(REPLAY.ADVERSARIAL_CASE.values()) <= set(BY_ID))

    def test_the_recorded_events_pass_every_oracle(self):
        result = REPLAY.evaluate(CASES, recorded_by_case())
        self.assertEqual(result["status"], "pass", result["failures"])
        self.assertEqual(len(result["cases"]), len(CASES))

    def test_the_adversarial_answers_still_pass_after_the_package_has_checked_them(self):
        for fixture, case_id in REPLAY.ADVERSARIAL_CASE.items():
            with self.subTest(fixture=fixture):
                result = REPLAY.evaluate([BY_ID[case_id]], {case_id: recorded(fixture)})
                self.assertEqual(result["status"], "pass", result["failures"])

    def test_a_missing_required_event_fails_its_rule(self):
        events = [event for event in recorded("ta_catch_count") if event.get("role") != "variable"]
        result = REPLAY.evaluate([BY_ID["catch_count"]], {"catch_count": events})
        self.assertEqual(result["status"], "fail")
        self.assertEqual(
            sorted(failure["rule_id"] for failure in result["failures"]),
            ["catch-count-variable", "catch-count-variable-prefill"],
        )
        self.assertTrue(all(failure["bucket"] == "required" for failure in result["failures"]))

    def test_a_forbidden_event_fails_its_rule(self):
        events = recorded("ta_catch_count") + [
            {"type": "selection", "role": "method", "iri": "https://w3id.org/smn/AnyMethod", "decision": "accept"}
        ]
        result = REPLAY.evaluate([BY_ID["catch_count"]], {"catch_count": events})
        self.assertEqual(result["status"], "fail")
        self.assertEqual(
            [(failure["bucket"], failure["rule_id"]) for failure in result["failures"]],
            [("forbidden", "no-catch-count-method-acceptance")],
        )

    def test_a_rule_matches_only_on_every_field_it_names(self):
        rule = BY_ID["catch_count"]["oracle"]["required"][0]
        event = {key: value for key, value in rule.items() if key != "rule_id"}
        self.assertTrue(REPLAY.event_matches_rule(event, rule))
        self.assertTrue(REPLAY.event_matches_rule(dict(event, extra="ignored"), rule))
        self.assertFalse(REPLAY.event_matches_rule(dict(event, decision="review"), rule))
        self.assertFalse(REPLAY.event_matches_rule({k: v for k, v in event.items() if k != "iri"}, rule))

    def test_an_unanswered_case_fails_every_required_rule_but_advisory_ones(self):
        result = REPLAY.evaluate(CASES, {})
        self.assertEqual(result["status"], "fail")
        failed = {(failure["case_id"], failure["rule_id"]) for failure in result["failures"]}
        for case in CASES:
            for rule in case["oracle"]["required"]:
                with self.subTest(rule=rule["rule_id"]):
                    self.assertEqual((case["case_id"], rule["rule_id"]) in failed, not rule.get("advisory"))
        self.assertFalse(any(failure["bucket"] == "forbidden" for failure in result["failures"]))

    def test_only_a_blocking_case_fails_the_run(self):
        case = copy.deepcopy(BY_ID["catch_count"])
        case["blocking"] = False
        result = REPLAY.evaluate([case], {})
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["cases"][0]["passed"])
        self.assertTrue(result["failures"])

    def test_scalar_keys_compare_as_the_r_benchmark_does(self):
        self.assertEqual(REPLAY.scalar_key(None), "<NA>")
        self.assertEqual(REPLAY.scalar_key(float("nan")), "<NA>")
        self.assertEqual(REPLAY.scalar_key(True), "true")
        self.assertEqual(REPLAY.scalar_key("accept"), "accept")


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.fixtures = self.directory / "v1"
        shutil.copytree(REPLAY.FIXTURES, self.fixtures)

    def check(self):
        with patch.object(REPLAY, "FIXTURES", self.fixtures):
            return REPLAY.check_manifest()

    def test_the_vendored_fixtures_match_metasalmons_manifest(self):
        cases = len(REPLAY.FIXTURE_CASE) + len(REPLAY.ADVERSARIAL_CASE)
        self.assertEqual(REPLAY.check_manifest(), cases * len(REPLAY.VENDORED_FILES))

    def test_an_edited_fixture_is_refused(self):
        answer = self.fixtures / "ta_catch_count" / "harness-1.csv"
        answer.write_bytes(answer.read_bytes().replace(b"accept", b"review", 1))
        with self.assertRaisesRegex(SystemExit, "ta_catch_count/harness-1.csv: SHA-256 differs"):
            self.check()

    def test_a_missing_or_extra_fixture_is_refused(self):
        (self.fixtures / "ta_gap" / "packet-1.json").unlink()
        (self.fixtures / "ta_gap" / "notes.txt").write_text("stray", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self.check()
        self.assertIn("ta_gap/packet-1.json: missing", str(raised.exception))
        self.assertIn("ta_gap/notes.txt: not one of the files the replay reads", str(raised.exception))

    def test_the_negative_control_answer_differs_only_on_the_variable(self):
        source = REPLAY.FIXTURES / "ta_catch_count" / "harness-1.csv"
        wrong = REPLAY.wrong_answer(source, self.directory / "wrong.csv")
        with source.open(newline="", encoding="utf-8") as handle:
            before = list(csv.DictReader(handle))
        with wrong.open(newline="", encoding="utf-8") as handle:
            after = list(csv.DictReader(handle))
        changed = [(old["dictionary_role"], new["llm_decision"]) for old, new in zip(before, after) if old != new]
        self.assertEqual(changed, [("variable", "review")])
        self.assertEqual(
            Path(f"{wrong}.packet-id").read_bytes(), Path(f"{source}.packet-id").read_bytes()
        )


class CohortTests(unittest.TestCase):
    """run_cohort's bookkeeping, with the package replay stubbed by recorded events."""

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def write_cohort(self, runs: dict[str, list[str]], guide: dict | None = None) -> Path:
        cohort = self.directory / "cohort"
        cohort.mkdir()
        for run_id, fixtures in runs.items():
            for fixture in fixtures:
                answer = cohort / run_id / fixture / "semantic-assessments-pass-1.csv"
                answer.parent.mkdir(parents=True)
                answer.write_text("stub\n", encoding="utf-8")
        record = {"runs": [{"run_id": run_id, "promoted_by": None} for run_id in runs]}
        if guide is not None:
            record["guide"] = guide
        (cohort / "cohort.json").write_text(json.dumps(record), encoding="utf-8")
        return cohort

    def score(self, cohort: Path) -> dict:
        def stub(fixture_case, answer, sidecar=None):
            return {"status": "complete", "findings": [], "events": recorded(fixture_case)}

        with patch.object(REPLAY, "replay", side_effect=stub):
            return REPLAY.run_cohort(cohort)

    def test_a_complete_run_passes(self):
        report = self.score(self.write_cohort({"run-a": list(REPLAY.FIXTURE_CASE.values())}))
        self.assertEqual(report["status"], "pass")
        self.assertEqual([run["status"] for run in report["runs"]], ["pass"])

    def test_a_run_missing_an_answer_fails_that_case(self):
        fixtures = [fixture for fixture in REPLAY.FIXTURE_CASE.values() if fixture != "ta_gap"]
        report = self.score(self.write_cohort({"run-a": list(REPLAY.FIXTURE_CASE.values()), "run-b": fixtures}))
        self.assertEqual(report["status"], "fail")
        self.assertEqual([run["status"] for run in report["runs"]], ["pass", "fail"])
        self.assertEqual(
            {failure["case_id"] for failure in report["runs"][1]["failures"]}, {"synthetic_structured_gap"}
        )

    def test_a_guide_edited_after_recording_is_reported_but_does_not_fail(self):
        skill = "skills/sdp-semantic-review/SKILL.md"
        current = "sha256:" + hashlib.sha256((ROOT / skill).read_bytes()).hexdigest()
        fixtures = list(REPLAY.FIXTURE_CASE.values())
        unchanged = self.score(self.write_cohort({"run-a": fixtures}, guide={skill: current}))
        self.assertEqual(unchanged["guide_changed_since_recorded"], [])
        shutil.rmtree(self.directory / "cohort")
        edited = self.score(self.write_cohort({"run-a": fixtures}, guide={skill: "sha256:" + "0" * 64}))
        self.assertEqual(edited["guide_changed_since_recorded"], [skill])
        self.assertEqual(edited["status"], "pass")

    def test_the_recorded_cohort_names_the_guide_it_ran_against(self):
        record = json.loads((REPLAY.COHORT / "cohort.json").read_text(encoding="utf-8"))
        self.assertIn("skills/sdp-semantic-review/references/judging.md", record["guide"])
        for run in record["runs"]:
            for fixture in REPLAY.FIXTURE_CASE.values():
                answer = REPLAY.COHORT / run["run_id"] / fixture / "semantic-assessments-pass-1.csv"
                with self.subTest(answer=str(answer.relative_to(ROOT))):
                    self.assertTrue(answer.is_file())
                    self.assertTrue(Path(f"{answer}.packet-id").is_file())

    def test_an_empty_cohort_is_refused(self):
        cohort = self.write_cohort({})
        with self.assertRaisesRegex(SystemExit, "records no runs"):
            self.score(cohort)


if __name__ == "__main__":
    unittest.main()
