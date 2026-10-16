"""Offline tests for metasalmon-skill's three review actions.

No package, network or model call: the package is a stand-in object, and
write_assessments runs against a real packet, the Theme A catch-count packet
vendored under evals/sdp-semantic-review/theme-a/. The live tests in
test_package_adapters.py run the same actions against the pinned release.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "evals" / "sdp-semantic-review" / "theme-a" / "v1" / "ta_catch_count" / "packet-1.json"


def load_adapter():
    spec = importlib.util.spec_from_file_location(
        "review_actions_adapter", ROOT / "skills" / "metasalmon-skill" / "scripts" / "metasalmon_api.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ADAPTER = load_adapter()


class RecordFrame:
    """The two things the ingest action asks of the package's record frame."""

    def __init__(self, rows):
        self.rows = rows
        self.columns = list(dict.fromkeys(key for row in rows for key in row))

    def __getitem__(self, names):
        return RecordFrame([{name: row.get(name) for name in names} for row in self.rows])

    def to_json(self, **_kwargs):
        return json.dumps(self.rows)


class SemanticReviewError(ValueError):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def run(payload, package):
    out = io.StringIO()
    with (
        patch.object(ADAPTER, "load_input", return_value=payload),
        patch.object(ADAPTER, "import_metasalmonpy", return_value=package),
        patch("sys.stdout", out),
    ):
        ADAPTER.main()
    return json.loads(out.getvalue())


class ReviewActionTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.review = self.directory / "sdp" / "review"
        self.review.mkdir(parents=True)
        self.packet_path = self.review / "semantic-review-packet.json"
        shutil.copy(PACKET, self.packet_path)
        self.packet = json.loads(self.packet_path.read_text(encoding="utf-8"))
        self.package = SimpleNamespace(
            __version__="0.6.0",
            SemanticReviewError=SemanticReviewError,
            write_semantic_review_packet=Mock(
                return_value={
                    "path": str(self.packet_path),
                    "packet_id": self.packet["packet_id"],
                    "pass": 1,
                    "units": 1,
                    "targets": 4,
                    "not_covered": [],
                }
            ),
            ingest_semantic_assessments=Mock(),
        )

    def slots(self):
        return [(unit["unit_key"], slot) for unit in self.packet["units"] for slot in unit["slots"]]

    def judgement(self, role, **values):
        (unit_key,) = {unit["unit_key"] for unit in self.packet["units"]}
        return {"unit_key": unit_key, "dictionary_role": role, **values}

    def write(self, judgements, **extra):
        payload = {
            "action": "write_assessments",
            "packet": str(self.packet_path),
            "provider": "claude-code",
            "model": "a-model",
            "judgements": judgements,
            **extra,
        }
        return run(payload, self.package)

    # build_review_packet ------------------------------------------------------

    def test_build_passes_the_request_to_the_package_and_names_the_answer_file(self):
        response = run(
            {
                "action": "build_review_packet",
                "path": str(self.directory / "sdp"),
                "sources": ["smn"],
                "context_text": "Fish were counted at the fence.",
                "top_n": 3,
            },
            self.package,
        )
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["engine"], "python")
        self.assertEqual(response["packet_id"], self.packet["packet_id"])
        self.assertEqual(response["answer_file"], str(self.review / "semantic-assessments-pass-1.csv"))
        self.package.write_semantic_review_packet.assert_called_once_with(
            str(self.directory / "sdp"),
            quiet=True,
            overwrite=False,
            sources=["smn"],
            context_text=["Fish were counted at the fence."],
            top_n=3,
        )

    def test_build_counts_the_code_values_it_left_out_by_column(self):
        left_out = [
            {"column_name": column, "dictionary_role": "entity", "target_sdp_field": "term_iri",
             "target_sdp_file": "codes.csv", "code_value": value, "slot_id": f"codes.csv|{column}/{value}|term_iri"}
            for column, values in (("WATERBODY", ["A", "B", "C", "D"]), ("SPECIES", ["Coho"]))
            for value in values
        ]
        self.package.write_semantic_review_packet.return_value["not_covered"] = left_out
        response = run({"action": "build_review_packet", "path": str(self.directory / "sdp")}, self.package)
        self.assertTrue(response["ok"], response)
        self.assertEqual(
            response["not_covered"],
            {
                "slots": 5,
                "columns": [
                    {"column_name": "WATERBODY", "dictionary_role": "entity", "target_sdp_field": "term_iri",
                     "code_values": 4, "examples": ["A", "B", "C"]},
                    {"column_name": "SPECIES", "dictionary_role": "entity", "target_sdp_field": "term_iri",
                     "code_values": 1, "examples": ["Coho"]},
                ],
            },
        )

    def test_build_refuses_malformed_controls_before_calling_the_package(self):
        for extra in (
            {},  # no path
            {"path": "sdp", "top_n": "3"},
            {"path": "sdp", "top_n": 0},
            {"path": "sdp", "sources": "smn"},
            {"path": "sdp", "overwrite": "false"},
            {"path": "sdp", "engine": "r"},
        ):
            with self.subTest(extra=extra):
                response = run({"action": "build_review_packet", **extra}, self.package)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_input")
        self.package.write_semantic_review_packet.assert_not_called()

    def test_a_release_without_the_contract_is_named(self):
        old = SimpleNamespace(__version__="0.5.0")
        for action in ("build_review_packet", "ingest_assessments"):
            with self.subTest(action=action):
                response = run({"action": action, "path": "sdp"}, old)
                self.assertEqual(response["error"]["code"], "invalid_input")
                self.assertIn("0.6.0", response["error"]["message"])

    # write_assessments ------------------------------------------------------

    def test_write_copies_identity_and_column_order_from_the_packet(self):
        roles = [slot["dictionary_role"] for _, slot in self.slots()]
        variable = next(slot for _, slot in self.slots() if slot["dictionary_role"] == "variable")
        judgements = [
            self.judgement(
                "variable",
                llm_decision="accept",
                llm_confidence=0.9,
                llm_selected_candidate_index=1,
                llm_selected_iri=variable["candidates"][0]["iri"],
            )
        ] + [self.judgement(role, llm_decision="review", llm_confidence=0.4) for role in roles[1:-1]]
        response = self.write(judgements)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["rows"], len(roles) - 1)
        self.assertEqual(response["unanswered"], [{"unit_key": self.slots()[-1][0], "dictionary_role": roles[-1]}])

        answer = self.review / "semantic-assessments-pass-1.csv"
        self.assertEqual(response["answer_file"], str(answer))
        with answer.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        self.assertEqual(reader.fieldnames, [column["name"] for column in self.packet["output"]["columns"]])
        self.assertEqual([row["dictionary_role"] for row in rows], roles[:-1])
        for row, (_, slot) in zip(rows, self.slots()):
            for name, value in slot["identity"].items():
                self.assertEqual(row[name], "" if value is None else value)
            self.assertEqual((row["llm_provider"], row["llm_model"]), ("claude-code", "a-model"))
        self.assertEqual(rows[0]["llm_selected_candidate_index"], "1")
        self.assertEqual(rows[0]["llm_selected_iri"], variable["candidates"][0]["iri"])
        package_owned = [c["name"] for c in self.packet["output"]["columns"] if c["owner"] == "package"]
        self.assertTrue(package_owned)
        self.assertTrue(all(row[name] == "" for row in rows for name in package_owned))
        sidecar = Path(f"{answer}.packet-id")
        self.assertEqual(sidecar.read_text(encoding="utf-8"), self.packet["packet_id"] + "\n")

    def test_write_refuses_what_the_packet_would_not_accept_and_writes_nothing(self):
        refusals = (
            [self.judgement("method_typo", llm_decision="review")],
            [self.judgement("variable", llm_decision="review"), self.judgement("variable", llm_decision="review")],
            [self.judgement("variable", llm_decison="review")],
            [self.judgement("variable", llm_decision="review", llm_selected_label="Catch abundance")],
            [self.judgement("variable", llm_decision="review", llm_confidence=True)],
            [self.judgement("variable", llm_decision="review", llm_rationale={"why": "no"})],
            "not a list",
        )
        for judgements in refusals:
            with self.subTest(judgements=judgements):
                response = self.write(judgements)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_input")
                self.assertFalse((self.review / "semantic-assessments-pass-1.csv").exists())
        for missing in ("provider", "model"):
            with self.subTest(missing=missing):
                response = self.write([self.judgement("variable", llm_decision="review")], **{missing: None})
                self.assertEqual(response["error"]["code"], "invalid_input")

    def test_write_keeps_an_existing_answer_file_unless_told_to_replace_it(self):
        first = self.write([self.judgement("variable", llm_decision="review")])
        self.assertTrue(first["ok"], first)
        again = self.write([self.judgement("variable", llm_decision="accept")])
        self.assertEqual(again["error"]["code"], "invalid_input")
        self.assertIn("overwrite", again["error"]["message"])
        replaced = self.write([self.judgement("variable", llm_decision="request_new_term")], overwrite=True)
        self.assertTrue(replaced["ok"], replaced)
        text = (self.review / "semantic-assessments-pass-1.csv").read_text(encoding="utf-8")
        self.assertIn("request_new_term", text)

    def test_write_passes_a_wrong_answer_through_for_the_package_to_judge(self):
        # Deciding is the package's job: an accept naming an IRI the packet did
        # not offer is written as given, and the ingester records it as an error.
        response = self.write(
            [self.judgement("variable", llm_decision="accept", llm_selected_candidate_index=9,
                            llm_selected_iri="https://example.org/not-offered")]
        )
        self.assertTrue(response["ok"], response)
        text = (self.review / "semantic-assessments-pass-1.csv").read_text(encoding="utf-8")
        self.assertIn("https://example.org/not-offered", text)

    def test_a_pass_2_packet_is_judged_only_where_it_says_reassess(self):
        # The package keeps a pass-1 answer for every slot that gained no
        # candidates and ignores a pass-2 row for it, so the adapter neither
        # asks for one nor writes one.
        packet = json.loads(self.packet_path.read_text(encoding="utf-8"))
        packet["pass"] = 2
        packet["output"]["file"] = "review/semantic-assessments-pass-2.csv"
        roles = [slot["dictionary_role"] for _, slot in self.slots()]
        for unit in packet["units"]:
            for slot in unit["slots"]:
                slot["reassess"] = slot["dictionary_role"] in roles[:2]
        self.packet_path = self.review / "semantic-review-packet-pass-2.json"
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        response = self.write([self.judgement(roles[0], llm_decision="review")])
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["answer_file"], str(self.review / "semantic-assessments-pass-2.csv"))
        self.assertEqual(
            response["unanswered"], [{"unit_key": self.slots()[1][0], "dictionary_role": roles[1]}]
        )

        refused = self.write([self.judgement(roles[2], llm_decision="review")], overwrite=True)
        self.assertEqual(refused["error"]["code"], "invalid_input")
        self.assertIn("reassess", refused["error"]["message"])

    # ingest_assessments -----------------------------------------------------

    def test_ingest_reports_status_next_packet_and_one_line_per_target(self):
        self.package.ingest_semantic_assessments.return_value = {
            "status": "awaiting_pass_2",
            "pass": 1,
            "packet_id": "abc",
            "next_packet": str(self.review / "semantic-review-packet-pass-2.json"),
            "summary": {"retries": 1},
            "findings": [],
            "assessments": RecordFrame(
                [{"dictionary_role": "variable", "llm_decision": "retry_search", "llm_rationale": "long text"}]
            ),
        }
        response = run(
            {"action": "ingest_assessments", "path": str(self.directory / "sdp"), "packet_id": "abc"},
            self.package,
        )
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["status"], "awaiting_pass_2")
        self.assertEqual(response["next_packet"], str(self.review / "semantic-review-packet-pass-2.json"))
        self.assertEqual(response["decisions"], [{"dictionary_role": "variable", "llm_decision": "retry_search"}])
        self.package.ingest_semantic_assessments.assert_called_once_with(
            str(self.directory / "sdp"), quiet=True, packet_id="abc"
        )

    def test_a_file_level_refusal_is_reported_with_its_code(self):
        self.package.ingest_semantic_assessments.side_effect = SemanticReviewError(
            "The file names a different packet.", "packet_mismatch"
        )
        response = run({"action": "ingest_assessments", "path": "sdp"}, self.package)
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "ingest_refused")
        self.assertEqual(response["refusal_code"], "packet_mismatch")

    def test_any_other_failure_stays_a_package_error(self):
        self.package.ingest_semantic_assessments.side_effect = RuntimeError("disk full")
        response = run({"action": "ingest_assessments", "path": "sdp"}, self.package)
        self.assertEqual(response["error"]["code"], "package_error")
        self.assertEqual(response["error"]["message"], "disk full")

    def test_catalog_lists_the_review_actions(self):
        response = run({"action": "catalog"}, self.package)
        for action in ("build_review_packet", "write_assessments", "ingest_assessments"):
            self.assertIn(action, response["actions"])


if __name__ == "__main__":
    unittest.main()
