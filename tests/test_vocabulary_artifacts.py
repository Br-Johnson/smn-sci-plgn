"""Independent RDF and workflow parsing; test-only dependencies, never runtime."""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "skills" / "controlled-vocabulary" / "scripts" / "controlled_vocabulary.py"


@unittest.skipUnless(importlib.util.find_spec("rdflib") and importlib.util.find_spec("yaml"), "RDF/workflow parser profile requires test-only rdflib and PyYAML; CI runs it separately")
class VocabularyArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "authoring"
        self.run_tool("init", self.project, "--demo")

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args):
        proc = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_independent_parsers_agree_on_every_rdf_representation(self):
        from rdflib import Graph, Literal, URIRef
        from rdflib.compare import isomorphic
        from rdflib.namespace import DCTERMS, OWL, RDF, SKOS

        path = self.project / "concepts.csv"
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream); fields, rows = reader.fieldnames, list(reader)
        definition = 'A fictional "quoted" category.\nSecond line with café & <angle>.'
        rows[0]["definition"] = definition
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fields, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
        site = self.root / "site"
        self.run_tool("build", self.project, "--output", site)
        for turtle in site.rglob("*.ttl"):
            with self.subTest(path=turtle.relative_to(site)):
                graph = Graph().parse(turtle, format="turtle")
                jsonld = Graph().parse(turtle.with_suffix(".jsonld"), format="json-ld")
                self.assertTrue(isomorphic(graph, jsonld))
        graph = Graph().parse(site / "vocabulary.ttl", format="turtle")
        term = URIRef("https://w3id.org/example-salmon-vocabulary/concept/demo-observation")
        self.assertIn((term, RDF.type, SKOS.Concept), graph)
        self.assertIn((term, SKOS.definition, Literal(definition, lang="en")), graph)
        self.assertIn((term, DCTERMS.source, URIRef("https://example.org/fictional-specification")), graph)
        retired = URIRef("https://w3id.org/example-salmon-vocabulary/concept/demo-retired")
        self.assertIn((retired, OWL.deprecated, Literal(True)), graph)

    def test_pages_workflow_is_manual_and_binding_checked(self):
        import yaml
        self.run_tool("release", self.project)
        output = self.root / "proposal"
        self.run_tool("prepare-publication", self.project, "--output", output)
        workflow = yaml.safe_load((output / "vocabulary-pages.yml").read_text())
        self.assertEqual(workflow["on"], {"workflow_dispatch": None})
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(workflow["jobs"]["deploy"]["needs"], "build")
        self.assertEqual(workflow["jobs"]["deploy"]["permissions"], {"contents": "read", "pages": "write", "id-token": "write"})
        commands = next(step["run"] for step in workflow["jobs"]["build"]["steps"] if "run" in step)
        self.assertIn("--for-publication --repository '${{ github.repository }}'", commands)

    def test_proposed_rewrite_rules_match_independent_expected_routes(self):
        self.run_tool("release", self.project)
        output = self.root / "proposal"
        self.run_tool("prepare-publication", self.project, "--output", output)
        rules = (output / "w3id" / "ids" / "example-salmon-vocabulary" / ".htaccess").read_text()
        cases = {
            "": "",
            "scheme": "",
            "vocabulary.ttl": "vocabulary.ttl",
            "vocabulary.jsonld": "vocabulary.jsonld",
            "concept/demo-observation": "concept/demo-observation/",
            "concept/demo-observation/index.ttl": "concept/demo-observation/index.ttl",
            "concept/demo-retired/index.jsonld": "concept/demo-retired/index.jsonld",
            "release/0.1.0": "releases/0.1.0/",
            "release/0.1.0/vocabulary.ttl": "releases/0.1.0/vocabulary.ttl",
            "release/0.1.0/manifest.json": "releases/0.1.0/manifest.json",
        }
        # This checks the generated subset as regexes, not Apache behavior or a
        # live W3ID deployment. Upstream's Apache check remains a publication gate.
        for requested, expected in cases.items():
            with self.subTest(path=requested):
                resolved = None
                for line in rules.splitlines():
                    if not line.startswith("RewriteRule "):
                        continue
                    _, pattern, target, flags = line.split()
                    match = re.fullmatch(pattern, requested)
                    if match:
                        self.assertEqual(flags, "[R=303,L]")
                        resolved = re.sub(r"\$(\d+)", lambda m: match[int(m[1])], target)
                        break
                self.assertEqual(resolved, "https://example-org.github.io/example-salmon-vocabulary/" + expected)


if __name__ == "__main__":
    unittest.main()
