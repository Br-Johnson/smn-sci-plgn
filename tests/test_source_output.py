"""Source JSON CLIs against invented HTTP responses, with sockets forbidden."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {
    "ptagis": ROOT / "skills/ptagis-skill/scripts/ptagis_api.py",
    "rmis": ROOT / "skills/rmis-skill/scripts/rmis_api.py",
    "npafc": ROOT / "skills/npafc-skill/scripts/npafc_catalog.py",
}
DRIVER = r'''
import pathlib, runpy, sys, urllib.request
body = pathlib.Path(sys.argv[2]).read_bytes()
class Response:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __init__(self, url): self.url = url
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return body
    def geturl(self): return self.url
def fixture(req, *args, **kwargs):
    return Response(req.full_url if hasattr(req, "full_url") else req)
def forbid_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo"}:
        raise AssertionError("source output fixture attempted real networking")
sys.addaudithook(forbid_network)
urllib.request.urlopen = fixture
urllib.request.OpenerDirector.open = fixture
runpy.run_path(sys.argv[1], run_name="__main__")
'''


class SourceOutputCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_source(self, source, payload, response, extra_env=None):
        path = self.directory / "response.json"
        path.write_text(json.dumps(response))
        environment = {key: value for key, value in os.environ.items() if key not in {
            "RMIS_API_KEY", "RMPC_API_KEY", "RMIS_JWT", "RMIS_EMAIL", "RMIS_PASSWORD",
            "PTAGIS_API_TOKEN", "PTAGIS_API_KEY", "STREAMNET_API_KEY",
        }}
        environment.update(extra_env or {})
        result = subprocess.run([sys.executable, "-c", DRIVER, str(SCRIPTS[source]), str(path)],
                                input=json.dumps(payload), text=True, capture_output=True,
                                env=environment, cwd=self.directory, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout, json.loads(result.stdout)

    def test_large_ptagis_response_returns_five_rows_with_bounded_serialized_bytes(self):
        rows = [{"row": i, "description": "fictional observation " + "é" * 4000} for i in range(1000)]
        rows[-1]["tail_marker"] = "bulk-only-fictional-row"
        stdout, result = self.run_source("ptagis", {"action": "interrogation_site_codes"}, rows)
        self.assertLessEqual(len(stdout.encode("utf-8")), 16384)
        self.assertEqual(len(result["records"]), 5)
        self.assertEqual(result["output"]["record_count"], 1000)
        self.assertEqual(result["output"]["preview_count"], 5)
        self.assertTrue(result["output"]["truncated"])
        self.assertEqual(result["source"], "PTAGIS API")
        self.assertTrue(result["url"].startswith("https://api.ptagis.org/"))
        self.assertNotIn("bulk-only-fictional-row", stdout)
        self.assertNotIn("sample", result["summary"])

    def test_rmis_and_npafc_bulk_envelopes_keep_metadata_with_only_preview_rows(self):
        rows = [{"id": i, "title": "fictional dataset", "notes": "x" * 2000} for i in range(1000)]
        cases = (
            ("rmis", {"action": "release"}, {"records": rows, "totalCount": 5000, "page": 2}, "records"),
            ("npafc", {"action": "dataset_search"}, {"success": True, "result": {"count": 5000, "results": rows}}, "results"),
            ("npafc", {"action": "dataset_show", "id": "fictional"}, {"success": True, "result": {**{f"metadata-{i}": "fictional metadata" for i in range(25)}, "resources": rows, "title": "Fictional dataset"}}, "resources"),
        )
        for source, request, response, collection in cases:
            with self.subTest(source=source):
                stdout, result = self.run_source(source, request, response)
                self.assertLessEqual(len(stdout.encode("utf-8")), 16384)
                self.assertEqual(len(result["records"][collection]), 5)
                self.assertEqual(result["output"]["record_count"], 1000)
                self.assertTrue(result["output"]["truncated"])
                if source == "rmis":
                    self.assertEqual(result["summary"]["totalCount"], 5000)
                    self.assertEqual(result["summary"]["page"], 2)
                elif request["action"] == "dataset_search":
                    self.assertEqual(result["summary"]["count"], 5000)
                else:
                    self.assertEqual(result["summary"]["resource_count"], 1000)

    def test_zero_one_row_and_compact_metadata_responses_remain_complete(self):
        for rows in ([], [{"id": "fictional-one", "title": "One fictional record"}]):
            for source, action, response, collection in (
                ("ptagis", "interrogation_site_codes", rows, None),
                ("rmis", "release", {"records": rows, "totalCount": len(rows)}, "records"),
                ("npafc", "dataset_search", {"success": True, "result": {"count": len(rows), "results": rows}}, "results"),
            ):
                with self.subTest(source=source, count=len(rows)):
                    _, result = self.run_source(source, {"action": action}, response)
                    shown = result["records"][collection] if collection else result["records"]
                    self.assertEqual(shown, rows)
                    self.assertEqual(result["output"]["record_count"], len(rows))
                    self.assertFalse(result["output"]["truncated"])
        metadata = {"name": "fictional-resource", "format": "CSV", "url": "https://example.invalid/fictional.csv"}
        _, result = self.run_source("npafc", {"action": "resource_show", "id": "fictional"}, {"success": True, "result": metadata})
        self.assertEqual(result["records"], metadata)
        self.assertEqual(result["summary"], metadata)
        self.assertFalse(result["output"]["truncated"])

    def test_npafc_generic_json_request_uses_the_same_bounded_output_contract(self):
        records = [{"id": i, "description": "fictional data " * 100} for i in range(1000)]
        stdout, result = self.run_source("npafc", {"action": "request", "url": "https://data.npafc.org/api/fixture"}, records)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["records"]), 5)
        self.assertEqual(result["summary"]["format"], "json")
        self.assertEqual(result["output"]["record_count"], 1000)
        self.assertLessEqual(len(stdout.encode("utf-8")), 16384)

    def test_full_stdout_requires_boolean_raw_opt_in(self):
        rows = [{"row": i, "description": "fictional data " * 40} for i in range(1000)]
        for raw in (False, "true", True):
            with self.subTest(raw=raw):
                stdout, result = self.run_source("ptagis", {"action": "interrogation_site_codes", "raw_stdout": raw}, rows)
                if raw is True:
                    self.assertEqual(result["records"], rows)
                    self.assertEqual(result["output"]["mode"], "raw")
                    self.assertFalse(result["output"]["truncated"])
                    self.assertGreater(len(stdout.encode("utf-8")), 16384)
                else:
                    self.assertLessEqual(len(stdout.encode("utf-8")), 16384)
                    self.assertEqual(len(result["records"]), 5)

    def test_local_raw_save_does_not_duplicate_bulk_results_in_stdout(self):
        rows = [{"row": i, "description": "fictional observation " * 30} for i in range(1000)]
        rows[-1]["marker"] = "local-only-fictional-tail"
        for source, action, response in (
            ("ptagis", "interrogation_site_codes", rows),
            ("rmis", "release", {"records": rows}),
            ("npafc", "dataset_search", {"success": True, "result": {"count": 1000, "results": rows}}),
        ):
            with self.subTest(source=source):
                target = self.directory / source / "saved.json"
                stdout, result = self.run_source(source, {"action": action, "save_raw": True, "raw_output_path": str(target)}, response)
                self.assertTrue(result["ok"])
                self.assertEqual(result["raw_output_path"], str(target))
                self.assertEqual(json.loads(target.read_text()), response)
                self.assertLessEqual(len(stdout.encode("utf-8")), 16384)
                self.assertNotIn("local-only-fictional-tail", stdout)

    def test_unwritable_save_target_returns_typed_error_and_compact_findings(self):
        rows = [{"row": i, "description": "fictional record"} for i in range(1000)]
        for source, action, response in (
            ("ptagis", "interrogation_site_codes", rows),
            ("rmis", "release", {"records": rows, "page": 3}),
            ("npafc", "dataset_search", {"success": True, "result": {"count": 1000, "results": rows}}),
        ):
            with self.subTest(source=source):
                # An existing directory deterministically cannot be opened as
                # a file, including when the test runner has elevated rights.
                stdout, result = self.run_source(source, {"action": action, "save_raw": True, "raw_output_path": str(self.directory)}, response)
                self.assertFalse(result["ok"])
                self.assertTrue(result["retrieval_ok"])
                self.assertEqual(result["error"]["code"], "raw_output_failed")
                self.assertIsNone(result["raw_output_path"])
                self.assertEqual(result["output"]["record_count"], 1000)
                self.assertTrue(result["records"])
                self.assertTrue(result["source"])
                self.assertTrue(result["url"].startswith("https://"))
                self.assertLessEqual(len(stdout.encode("utf-8")), 16384)

    def test_byte_budget_fallback_preserves_the_save_error_receipt(self):
        # Large valid JSON numbers cannot be shortened as text previews can.
        # The final compact receipt must still identify a failed local save.
        response = [{f"value-{i}": 10 ** 3000 for i in range(12)}]
        stdout, result = self.run_source("ptagis", {"action": "interrogation_site_codes", "save_raw": True, "raw_output_path": str(self.directory)}, response)
        self.assertLessEqual(len(stdout.encode("utf-8")), 16384)
        self.assertEqual(result["error"]["code"], "raw_output_failed")
        self.assertTrue(result["retrieval_ok"])
        self.assertEqual(result["output"]["record_count"], 1)
        self.assertEqual(result["output"]["preview_count"], 0)
        self.assertTrue(result["output"]["truncated"])
        self.assertTrue(result["url"].startswith("https://api.ptagis.org/"))

    def test_raw_opt_in_and_local_save_keep_existing_credential_redaction(self):
        token = "invented-source-output-token-8q2"
        response = {"records": [{"name": "public fixture", "note": token, "access_token": "invented-response-secret-9t3"}]}
        target = self.directory / "redacted.json"
        stdout, result = self.run_source("ptagis", {"action": "interrogation_site_codes", "raw_stdout": True, "save_raw": True, "raw_output_path": str(target)}, response,
                                         {"PTAGIS_API_TOKEN": token})
        for secret in (token, "invented-response-secret-9t3"):
            self.assertNotIn(secret, stdout + target.read_text())
        self.assertEqual(result["records"]["records"][0]["name"], "public fixture")
        self.assertEqual(json.loads(target.read_text())["records"][0]["access_token"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
