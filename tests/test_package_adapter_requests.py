"""Public request contracts reconciled from PR #3 against the released SDK.

The released profile shares the snapshot suite's provenance check and refused
network boundary. These tests exercise JSON subprocesses, not fake SDK calls.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_term_snapshot_controls as snapshots


ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "skills/salmon-terms/scripts/salmon_terms.py"
SDP = ROOT / "skills/metasalmon-skill/scripts/metasalmon_api.py"


class OfflineAdapterRequestTests(unittest.TestCase):
    def adapter_without_package(self, script, payload):
        env = {key: value for key, value in os.environ.items()
               if not key.endswith(("API_KEY", "API_TOKEN", "AUTH_TOKEN", "PASSWORD"))}
        env.pop("PYTHONPATH", None)
        process = subprocess.run(
            [sys.executable, "-S", str(script)], input=json.dumps(payload), env=env,
            text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn("Traceback", process.stderr)
        return json.loads(process.stdout)

    def test_malformed_common_controls_are_json_before_dependency_loading(self):
        for script in (TERMS, SDP):
            for payload in ({"save_raw": "false"}, {"save_raw": None},
                            {"action": []}, {"action": ""},
                            {"raw_output_path": {}}, {"raw_output_path": ""}):
                with self.subTest(script=script.name, payload=payload):
                    result = self.adapter_without_package(script, payload)
                    self.assertEqual(result["error"]["code"], "invalid_input")

    def test_valid_common_controls_keep_the_missing_package_diagnostic(self):
        for script in (TERMS, SDP):
            with self.subTest(script=script.name):
                result = self.adapter_without_package(script, {"action": "runtime", "save_raw": False})
                self.assertEqual(result["error"]["code"], "missing_package")


@unittest.skipUnless(snapshots.ENABLED, "requires the actual pinned package profile")
class ReleasedAdapterRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshots.SnapshotAdapterTests.setUpClass()

    def adapter(self, script, payload):
        return snapshots.SnapshotAdapterTests.run_python(
            "import runpy, sys; from metasalmonpy import sdp_schema; "
            "sdp_schema.set_sdp_schema_source('vendored'); "
            "runpy.run_path(sys.argv[1], run_name='__main__')",
            script, payload=payload,
        )

    def snapshot_request(self, **controls):
        return {
            "action": "find_terms", "query": "escapement", "sources": ["smn"],
            "expand_query": False, "release": {"smn": "0.0.3"},
            "snapshot_dir": {"smn": str(ROOT / "tests/fixtures/ontology-releases/smn-0.0.3")},
            **controls,
        }

    def test_boolean_controls_refuse_strings_numbers_and_null(self):
        for value in ("false", 0, None):
            for script, payload in (
                (TERMS, self.snapshot_request(expand_query=value)),
                (SDP, {"action": "validate_salmon_datapackage", "path": "not-an-sdp",
                       "require_iris": value}),
            ):
                with self.subTest(script=script.name, value=value):
                    response = self.adapter(script, payload)
                    self.assertFalse(response["ok"])
                    self.assertEqual(response["error"]["code"], "invalid_input")

    def test_preview_limit_requires_a_positive_json_integer(self):
        for value in (-1, 0, True, "2", 1.2):
            with self.subTest(value=value):
                response = self.adapter(TERMS, self.snapshot_request(max_items=value))
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_input")

    def test_valid_false_and_positive_limit_preserve_snapshot_provenance(self):
        response = self.adapter(TERMS, self.snapshot_request(max_items=1))
        self.assertTrue(response["ok"])
        self.assertIs(response["expand_query"], False)
        self.assertEqual((response["count"], response["total"]), (1, 1))
        self.assertEqual(response["ontology_release"][0]["version"], "0.0.3")
        self.assertTrue(response["ontology_release"][0]["manifest_verified"])
        self.assertEqual(response["runtime"]["package_version"], "0.6.0")

    def test_existing_source_name_and_normalized_array_contract_is_preserved(self):
        baseline = self.adapter(TERMS, self.snapshot_request())
        for sources in (" SMN ", [None, "", " SMN ", "smn"]):
            with self.subTest(sources=sources):
                response = self.adapter(TERMS, self.snapshot_request(sources=sources))
                self.assertTrue(response["ok"])
                for key in ("results", "ontology_release"):
                    self.assertEqual(response[key], baseline[key])
                diagnostic = response["diagnostics"][0]
                self.assertEqual((diagnostic["source"], diagnostic["status"], diagnostic["count"]),
                                 ("smn", "success", 1))

    def test_valid_validation_booleans_preserve_the_packages_strict_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft-sdp"
            snapshots.SnapshotAdapterTests.run_python("""
import contextlib, io, json, sys, warnings
import pandas as pd
import metasalmonpy as ms
from metasalmonpy import sdp_schema
sdp_schema.set_sdp_schema_source("vendored")
with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
    warnings.simplefilter("ignore")
    ms.create_sdp(pd.DataFrame({"stream": ["Example Creek"], "count": [3]}),
                  sys.argv[1], dataset_id="fictional-counts", seed_semantics=False,
                  check_updates=False)
print(json.dumps({"created": True}))
""", path)
            request = {"action": "validate_salmon_datapackage", "path": str(path)}
            ordinary = self.adapter(SDP, {**request, "require_iris": False})
            strict = self.adapter(SDP, {**request, "require_iris": True})
            self.assertTrue(ordinary["ok"], ordinary)
            self.assertFalse(strict["ok"], strict)
            self.assertIs(ordinary["require_iris"], False)
            self.assertIs(strict["require_iris"], True)
            self.assertEqual(strict["error"]["code"], "validation_failed")

    def test_save_failure_keeps_findings_and_runtime_in_one_json_response(self):
        with tempfile.TemporaryDirectory() as directory:
            for script, payload, findings in (
                (TERMS, self.snapshot_request(), "results"),
                (SDP, {"action": "catalog"}, "exports"),
            ):
                with self.subTest(script=script.name):
                    response = self.adapter(script, {**payload, "save_raw": True,
                                                     "raw_output_path": directory})
                    self.assertFalse(response["ok"])
                    self.assertEqual(response["error"]["code"], "raw_output_failed")
                    self.assertIsNone(response["raw_output_path"])
                    self.assertNotIn(directory, response["error"]["message"])
                    self.assertEqual(response["runtime"]["package_version"], "0.6.0")
                    self.assertTrue(response[findings])

    def test_successful_save_contains_the_sdk_findings_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            for script, payload, fields in (
                (TERMS, self.snapshot_request(), ("results", "diagnostics", "ontology_release")),
                (SDP, {"action": "catalog"}, ("exports", "actions")),
            ):
                with self.subTest(script=script.name):
                    destination = Path(directory) / script.name / "result.json"
                    response = self.adapter(script, {**payload, "save_raw": True,
                                                     "raw_output_path": str(destination)})
                    self.assertTrue(response["ok"])
                    self.assertEqual(response["raw_output_path"], str(destination))
                    saved = json.loads(destination.read_text())
                    for key in (*fields, "runtime"):
                        self.assertEqual(saved[key], response[key])

    def test_false_save_flag_does_not_write_an_explicit_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "unused.json"
            for script in (TERMS, SDP):
                with self.subTest(script=script.name):
                    response = self.adapter(script, {"action": "runtime", "save_raw": False,
                                                     "raw_output_path": str(destination)})
                    self.assertTrue(response["ok"])
                    self.assertIsNone(response["raw_output_path"])
                    self.assertFalse(destination.exists())

    def test_text_and_fallback_controls_are_not_coerced_into_requests(self):
        for script, payload in (
            (TERMS, self.snapshot_request(query=["escapement"])),
            (TERMS, self.snapshot_request(role={"variable": True})),
            (SDP, {"action": "validate_salmon_datapackage", "path": ["not-an-sdp"]}),
            (SDP, {"action": "fetch_salmon_ontology", "url": ["https://example.invalid/"]}),
            (SDP, {"action": "fetch_salmon_ontology", "url": "https://example.invalid/",
                   "cache_dir": {"path": "not-a-path"}}),
            (SDP, {"action": "fetch_salmon_ontology", "url": "https://example.invalid/",
                   "fallback_urls": "https://example.invalid/fallback"}),
        ):
            with self.subTest(script=script.name, payload=payload):
                response = self.adapter(script, payload)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
