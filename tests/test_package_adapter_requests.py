"""Offline request/response contracts; no package, source, or model calls."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_adapter(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TERMS = load_adapter("skills/salmon-terms/scripts/salmon_terms.py", "request_test_terms")
SDP = load_adapter("skills/metasalmon-skill/scripts/metasalmon_api.py", "request_test_sdp")


class RecordedFrame:
    """Only the JSON/DataFrame boundary is faked; ordering is observable."""

    columns = ["iri"]
    attrs = {"diagnostics": [{"source": "fixture", "status": "ok"}]}

    def to_json(self, **_kwargs):
        return json.dumps([{"iri": f"urn:fixture:{i}"} for i in range(3)])


class AdapterRequestTests(unittest.TestCase):
    def setUp(self):
        self.package = SimpleNamespace(
            __version__="0.5.0",
            find_terms=Mock(return_value=RecordedFrame()),
            sources_for_role=Mock(return_value=["fixture"]),
            validate_salmon_datapackage=Mock(
                return_value={"issues": [], "semantic_validation": {"status": "fixture"}}
            ),
            fetch_salmon_ontology=Mock(),
        )

    def run_adapter(self, module, payload):
        out = io.StringIO()
        with (
            patch.object(module, "load_input", return_value=payload),
            patch.object(module, "import_metasalmonpy", return_value=self.package),
            patch("sys.stdout", out),
        ):
            module.main()
        return json.loads(out.getvalue())

    def test_valid_controls_reach_package_without_ranking_or_expansion_change(self):
        response = self.run_adapter(
            TERMS,
            {"query": "fixture", "max_items": 2, "expand_query": False, "sources": ["fixture"]},
        )
        self.assertTrue(response["ok"])
        self.assertEqual(response["total"], 3)
        self.assertEqual(response["count"], 2)
        self.assertEqual(response["results"], [{"iri": "urn:fixture:0"}, {"iri": "urn:fixture:1"}])
        self.assertEqual(response["diagnostics"], RecordedFrame.attrs["diagnostics"])
        self.package.find_terms.assert_called_once_with(
            "fixture", role=None, sources=["fixture"], expand_query=False
        )

    def test_malformed_boolean_never_starts_search_or_validation(self):
        for value in ("false", 0, None):
            for module, payload, operation in (
                (TERMS, {"query": "fixture", "expand_query": value}, self.package.find_terms),
                (
                    SDP,
                    {"action": "validate_salmon_datapackage", "path": "fixture", "require_iris": value},
                    self.package.validate_salmon_datapackage,
                ),
            ):
                with self.subTest(value=value, module=module.__name__):
                    response = self.run_adapter(module, payload)
                    self.assertFalse(response["ok"])
                    self.assertEqual(response["error"]["code"], "invalid_input")
                    operation.assert_not_called()

    def test_strict_validation_boolean_reaches_package(self):
        response = self.run_adapter(
            SDP, {"action": "validate_salmon_datapackage", "path": "fixture", "require_iris": True}
        )
        self.assertTrue(response["ok"])
        self.package.validate_salmon_datapackage.assert_called_once_with("fixture", require_iris=True)

    def test_non_positive_or_non_integer_limit_never_starts_search(self):
        for value in (-1, 0, True, "2", 1.2):
            with self.subTest(value=value):
                response = self.run_adapter(TERMS, {"query": "fixture", "max_items": value})
                self.assertEqual(response["error"]["code"], "invalid_input")
        self.package.find_terms.assert_not_called()

    def test_malformed_source_lists_and_query_never_start_search(self):
        for patch_payload in (
            {"sources": "fixture"},
            {"sources": ["fixture", 3]},
            {"sources": [""]},
            {"query": ["fixture"]},
            {"role": {"variable": True}},
        ):
            with self.subTest(patch_payload=patch_payload):
                response = self.run_adapter(TERMS, {"query": "fixture", **patch_payload})
                self.assertEqual(response["error"]["code"], "invalid_input")
        self.package.find_terms.assert_not_called()

    def test_malformed_fallback_never_fetches_ontology(self):
        response = self.run_adapter(
            SDP,
            {"action": "fetch_salmon_ontology", "url": "urn:fixture", "fallback_urls": "urn:other"},
        )
        self.assertEqual(response["error"]["code"], "invalid_input")
        self.package.fetch_salmon_ontology.assert_not_called()

    def test_common_request_errors_are_json_before_import(self):
        for module in (TERMS, SDP):
            for payload in ({"save_raw": "false"}, {"action": []}, {"raw_output_path": {}}):
                with self.subTest(module=module.__name__, payload=payload):
                    out = io.StringIO()
                    with (
                        patch.object(module, "load_input", return_value=payload),
                        patch.object(module, "import_metasalmonpy") as importer,
                        patch("sys.stdout", out),
                    ):
                        module.main()
                    self.assertEqual(json.loads(out.getvalue())["error"]["code"], "invalid_input")
                    importer.assert_not_called()

    def test_save_failure_is_json_and_keeps_findings_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            for module, payload in (
                (TERMS, {"query": "fixture"}),
                (SDP, {"action": "validate_salmon_datapackage", "path": "fixture"}),
            ):
                with self.subTest(module=module.__name__):
                    response = self.run_adapter(
                        module, {**payload, "save_raw": True, "raw_output_path": directory}
                    )
                    self.assertFalse(response["ok"])
                    self.assertEqual(response["error"]["code"], "raw_output_failed")
                    self.assertIsNone(response["raw_output_path"])
                    self.assertEqual(response["runtime"]["package_version"], "0.5.0")
                    self.assertIn("results" if module is TERMS else "semantic_validation", response)

    def test_saved_output_contains_package_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "receipt.json"
            response = self.run_adapter(
                TERMS, {"query": "fixture", "save_raw": True, "raw_output_path": str(destination)}
            )
            self.assertTrue(response["ok"])
            saved = json.loads(destination.read_text())
            self.assertEqual(saved["results"], response["results"])
            self.assertEqual(saved["diagnostics"], response["diagnostics"])
            self.assertEqual(saved["runtime"], response["runtime"])

    def test_package_value_error_remains_package_error(self):
        self.package.find_terms.side_effect = ValueError("fixture package refusal")
        response = self.run_adapter(TERMS, {"query": "fixture"})
        self.assertEqual(response["error"]["code"], "package_error")
        self.assertEqual(response["error"]["message"], "fixture package refusal")


if __name__ == "__main__":
    unittest.main()
