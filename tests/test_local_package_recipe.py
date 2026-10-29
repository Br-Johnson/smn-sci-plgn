"""Run the fictional recipe through its subprocess seam, using a real SDK."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "skills/metasalmon-skill/examples/local_csv_recipe.py"
FIXTURE = EXAMPLE.parent / "fictional-counts.csv"
PYTHON = os.environ.get("SMN_RECIPE_PYTHON") or (sys.executable if importlib.util.find_spec("metasalmonpy") else None)
SPEC_VALIDATOR = os.environ.get("SMN_RECIPE_SDP_VALIDATOR")
SPEC_PYTHON = os.environ.get("SMN_RECIPE_SDP_PYTHON") or PYTHON
DRIVER = r'''
import runpy, sys
from pathlib import Path
def no_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "urllib.Request", "http.client.connect"}:
        raise AssertionError("local recipe attempted a provider or network request")
sys.addaudithook(no_network)
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent))
runpy.run_path(sys.argv[0], run_name="__main__")
'''


@unittest.skipUnless(PYTHON, "set SMN_RECIPE_PYTHON to an isolated metasalmonpy v0.6.0 [eml] interpreter")
class LocalPackageRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name) / "recipe"

    def tearDown(self):
        self.temp.cleanup()

    def recipe(self, *args, expected=0):
        environment = {key: value for key, value in os.environ.items() if not key.endswith(("API_KEY", "AUTH_TOKEN"))}
        proc = subprocess.run([PYTHON, "-c", DRIVER, str(EXAMPLE), *map(str, args)], text=True,
                              capture_output=True, timeout=60, env=environment)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_csv_draft_is_created_by_sdk_and_fails_strict_validation(self):
        result = self.recipe("draft", self.work)
        self.assertEqual(result["sdk_version"], "0.6.0")
        self.assertTrue(result["strict_draft_refused"])
        self.assertIn("term_iri", result["strict_draft_message"])
        self.assertEqual((self.work / "original.csv").read_bytes(), FIXTURE.read_bytes())
        self.assertTrue((self.work / "draft-sdp/datapackage.json").is_file())
        self.assertFalse((self.work / "reviewed-sdp").exists())
        self.assertFalse((self.work / "draft-sdp/reviewed_semantic_selections.csv").exists())

    def test_review_cannot_accept_semantics_from_a_prompt_or_without_confirmation(self):
        self.recipe("draft", self.work)
        before = {p.relative_to(self.work): p.read_bytes() for p in self.work.rglob("*") if p.is_file()}
        result = self.recipe("review", self.work, expected=1)
        self.assertIn("human_confirmation_required", result["error"])
        after = {p.relative_to(self.work): p.read_bytes() for p in self.work.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_confirmed_fictional_recipe_round_trips_qualifiers_sidecars_and_exports_eml(self):
        self.recipe("draft", self.work)
        original = (self.work / "original.csv").read_bytes()
        result = self.recipe("review", self.work, "--confirm-fictional-semantics")
        self.assertTrue(result["strict_reviewed"])
        self.assertTrue(result["strict_rewritten"])
        self.assertTrue(result["eml"]["xsd_valid"])
        self.assertFalse(result["publication_performed"])
        self.assertEqual((self.work / "original.csv").read_bytes(), original)
        for relative in ("metadata/semantic_vocabulary.csv", "reviewed_semantic_selections.csv", "metadata/eml-mapping.yml", "README-review.txt"):
            self.assertEqual((self.work / "reviewed-sdp" / relative).read_bytes(), (self.work / "rewritten-sdp" / relative).read_bytes())
        import csv
        with (self.work / "rewritten-sdp/metadata/column_dictionary.csv").open() as stream:
            row = next(r for r in csv.DictReader(stream) if r["column_name"] == "adult_count_sum")
        self.assertEqual(row["constraint_iri"], "https://example.org/fictional-sdp/Adult")
        self.assertEqual(row["statistical_modifier_iri"], "https://example.org/fictional-sdp/Sum")
        self.assertTrue((self.work / "rewritten-sdp/metadata/eml.xml").is_file())
        xsd_check = r'''
import json, sys
from pathlib import Path
import metasalmonpy as ms
from lxml import etree
schema_path = Path(ms.__file__).parent / "data/xsd/eml-2.2.0/eml.xsd"
parser = etree.XMLParser(no_network=True)
schema = etree.XMLSchema(etree.parse(str(schema_path), parser))
document = etree.parse(sys.argv[1], parser)
schema.assertValid(document)
print(json.dumps({"valid": True, "root": document.getroot().tag}))
'''
        proc = subprocess.run([PYTHON, "-c", xsd_check, str(self.work / "rewritten-sdp/metadata/eml.xml")],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {"valid": True, "root": "{https://eml.ecoinformatics.org/eml-2.2.0}eml"})

    @unittest.skipUnless(SPEC_VALIDATOR, "set SMN_RECIPE_SDP_VALIDATOR to the independently checked-out SDP validate_package.py")
    def test_created_reviewed_and_rewritten_packages_pass_the_independent_sdp_spec(self):
        self.recipe("draft", self.work)
        self.recipe("review", self.work, "--confirm-fictional-semantics")
        for folder in ("reviewed-sdp", "rewritten-sdp"):
            with self.subTest(folder=folder):
                proc = subprocess.run([SPEC_PYTHON, "-c", DRIVER, SPEC_VALIDATOR, str(self.work / folder)],
                                      capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("Strict SDP validation passed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
