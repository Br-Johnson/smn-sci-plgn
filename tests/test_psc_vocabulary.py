"""PSC discovery contract through the JSON CLI, with synthetic releases only."""
from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "skills/psc-vocabulary/scripts/psc_vocabulary.py"
FIXTURE = ROOT / "tests/fixtures/psc-vocabulary"


class PscVocabularyCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        shutil.copytree(FIXTURE, self.source)

    def call(self, **request):
        payload = {"action": "lookup", "source_config": str(self.source / "source.json"),
                   "authorized": True, "query": "Fictional count"} | request
        env = dict(os.environ)
        env.pop("PSC_VOCABULARY_SOURCE", None)
        result = subprocess.run([sys.executable, str(ADAPTER)], input=json.dumps(payload),
                                capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_current_term_keeps_exact_definition_and_verified_release_provenance(self):
        result = self.call()
        self.assertTrue(result["ok"], result)
        term = result["results"][0]
        self.assertEqual(term["iri"], "https://w3id.org/psc/vocab/concept/PSC-CV-900001")
        self.assertEqual(term["definition"], "The exact fictional count definition.")
        self.assertEqual(result["source"]["release_version"], "v0.0.0-synthetic.1")
        self.assertTrue(result["source"]["all_artifact_hashes_verified"])
        self.assertEqual(term["review"]["term_status"], "provisional")

    def test_a_pinned_catalog_cannot_rewrite_the_released_definition(self):
        path = self.source / "catalog.json"
        catalog = json.loads(path.read_text())
        catalog["terms"][0]["definition"] = "An invented definition not present in the release."
        path.write_text(json.dumps(catalog))
        descriptor = self.source / "source.json"
        config = json.loads(descriptor.read_text())
        config["catalog_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        descriptor.write_text(json.dumps(config))
        result = self.call()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "source_invalid")
        self.assertNotIn("results", result)

    def test_legacy_identity_uses_only_explicit_reuse_and_mappings_never_canonicalize(self):
        legacy = self.call(query="PSC-CV-900002")["results"][0]
        self.assertEqual(legacy["iri"], "https://example.org/source#FictionalWeight")
        self.assertEqual(legacy["definition"], "The exact upstream fictional weight definition.")
        self.assertEqual(legacy["identity_basis"], "explicit_concept_reuse")
        self.assertEqual(legacy["legacy_records"][0]["lifecycle_status"], "deprecated")
        self.assertEqual(legacy["reuse_decisions"][0]["selection_status"], "draft")
        current = self.call()["results"][0]
        self.assertEqual(current["iri"], "https://w3id.org/psc/vocab/concept/PSC-CV-900001")
        self.assertEqual({row["workflow_status"] for row in current["mapping_reviews"]},
                         {"candidate", "rejected", "deferred", "prototype_accepted"})
        self.assertTrue(all(row["canonicalizes"] is False for row in current["mapping_reviews"]))
        self.assertEqual(self.call(query="https://example.org/mapping#candidate")["total"], 0)

    def test_prototype_acceptance_remains_provisional_pending_and_not_adopted(self):
        term = self.call(query="Fictional prototype measure")["results"][0]
        self.assertEqual(term["review"]["term_status"], "provisional")
        self.assertEqual(term["review"]["approval_status"], "prototype_accepted")
        self.assertEqual(term["review"]["domain_review_status"], "pending")
        self.assertEqual(term["review"]["adoption_status"], "not_adopted")
        self.assertEqual(term["selections"][0]["selection_status"], "draft")

    def test_stock_kind_never_becomes_a_stock_record(self):
        term = self.call(query="Fictional stock kind")["results"][0]
        self.assertEqual(term["entity_role"], "stock_kind")
        self.assertIs(term["is_stock_record"], False)
        self.assertIn("individual stock", term["identity_note"])
        refused = self.call(entity_role="stock_record")
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["error"]["code"], "unsupported_role")

    def test_refused_missing_and_unreadable_sources_are_unavailable_not_no_results(self):
        for fields, code in [({"authorized": False}, "permission_refused"),
                             ({"authorized": "yes"}, "permission_refused"),
                             ({"source_config": str(self.source / "absent.json")}, "source_unavailable"),
                             ({"source_config": ""}, "source_unavailable")]:
            with self.subTest(code=code, fields=fields):
                response = self.call(**fields)
                self.assertFalse(response["ok"])
                self.assertEqual(response["status"], "unavailable")
                self.assertEqual(response["error"]["code"], code)
                self.assertNotIn("results", response)

    def test_modified_manifest_catalog_and_any_artifact_are_refused(self):
        for name in ["release/manifest.json", "catalog.json", "release/NOTICE.md"]:
            with self.subTest(name=name):
                target = self.source / name
                before = target.read_bytes()
                target.write_bytes(before + b"tampered")
                response = self.call()
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "source_invalid")
                self.assertNotIn("results", response)
                target.write_bytes(before)

    def test_incomplete_pinned_release_is_not_a_successful_empty_search(self):
        manifest_path = self.source / "release/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["artifacts"] = [row for row in manifest["artifacts"] if row["path"] != "external-mapping-review.csv"]
        manifest_path.write_text(json.dumps(manifest))
        config_path = self.source / "source.json"
        config = json.loads(config_path.read_text())
        config["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        config_path.write_text(json.dumps(config))
        response = self.call(query="nonexistent synthetic term")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "source_invalid")

    def test_valid_empty_lookup_and_bounded_results_remain_distinct_from_failure(self):
        empty = self.call(query="there is no such synthetic term")
        self.assertTrue(empty["ok"])
        self.assertEqual((empty["total"], empty["results"]), (0, []))
        bounded = self.call(query="Fictional", max_items=1)
        self.assertEqual((bounded["total"], len(bounded["results"])), (4, 1))
        self.assertEqual(bounded["results"][0]["label"], "Fictional count")

    def test_input_controls_and_runtime_need_no_source(self):
        for fields in [{"action": "change_mapping"}, {"query": ""}, {"max_items": True}, {"max_items": 0}]:
            with self.subTest(fields=fields):
                self.assertEqual(self.call(**fields)["error"]["code"], "invalid_input")
        runtime = self.call(action="runtime", source_config="", authorized=False)
        self.assertTrue(runtime["read_only"])
        self.assertFalse(runtime["network"])


if __name__ == "__main__":
    unittest.main()
