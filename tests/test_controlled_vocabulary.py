"""Exercise the local authoring workflow through its portable CLI."""

from __future__ import annotations

import json
import csv
import os
from html.parser import HTMLParser
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills" / "controlled-vocabulary" / "scripts" / "controlled_vocabulary.py"


class ControlledVocabularyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.project = self.base / "vocabulary"
        # Refuse accidental networking at the system boundary in every CLI run.
        (self.base / "sitecustomize.py").write_text(
            "import sys\ndef offline(event, args):\n"
            "    if event in {'socket.connect','socket.getaddrinfo','urllib.Request'}:\n"
            "        raise RuntimeError('network is forbidden in this local fixture')\n"
            "sys.addaudithook(offline)\n"
        )

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args, expected=0):
        proc = subprocess.run(
            [sys.executable, str(TOOL), *map(str, args)],
            text=True, capture_output=True, timeout=30, check=False,
            env=dict(os.environ, PYTHONPATH=str(self.base)),
        )
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def edit_terms(self, update):
        path = self.project / "concepts.csv"
        with path.open(newline="") as source:
            reader = csv.DictReader(source)
            fields, rows = reader.fieldnames, list(reader)
        update(rows)
        with path.open("w", newline="") as dest:
            writer = csv.DictWriter(dest, fields, lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)

    def test_demo_can_be_authored_and_validated_without_registration(self):
        created = self.run_tool("init", self.project, "--demo")
        checked = self.run_tool("validate", self.project)
        self.assertEqual(checked["concept_count"], 2)
        self.assertEqual(checked["namespace"], "https://w3id.org/example-salmon-vocabulary/")
        self.assertFalse(created["publication_performed"])
        self.assertEqual(checked["namespace_collision_check"], "not_performed")
        self.assertTrue((self.project / "tools" / "controlled_vocabulary.py").is_file())

    def test_prepared_release_and_website_are_reproducible_and_keep_term_identity(self):
        self.run_tool("init", self.project, "--demo")
        released = self.run_tool("release", self.project)
        self.assertFalse(released["publication_performed"])
        first, second = self.base / "first", self.base / "second"
        self.run_tool("build", self.project, "--output", first)
        self.run_tool("build", self.project, "--output", second)
        first_files = {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()}
        second_files = {p.relative_to(second): p.read_bytes() for p in second.rglob("*") if p.is_file()}
        self.assertEqual(first_files, second_files)
        self.assertTrue((first / "releases" / "0.1.0" / "manifest.json").is_file())
        graph = json.loads((first / "vocabulary.jsonld").read_text())["@graph"]
        term = next(item for item in graph if item["@id"].endswith("/concept/demo-observation"))
        self.assertEqual(term["@type"], "skos:Concept")
        self.assertEqual(term["skos:prefLabel"], {"@value": "Demo observation category", "@language": "en"})
        self.assertEqual(term["dcterms:source"], {"@id": "https://example.org/fictional-specification"})
        self.assertTrue((first / "concept" / "demo-observation" / "index.html").is_file())

    def test_unknown_broader_target_is_refused_before_release_writes(self):
        self.run_tool("init", self.project, "--demo")
        self.edit_terms(lambda rows: rows[0].update(broader="not-a-concept"))
        refused = self.run_tool("release", self.project, expected=1)
        self.assertIn("broader", refused["error"])
        self.assertFalse((self.project / "releases").exists())

    def test_new_release_cannot_withdraw_a_previously_released_identifier(self):
        self.run_tool("init", self.project, "--demo")
        self.run_tool("release", self.project)
        config = self.project / "vocabulary.json"
        meta = json.loads(config.read_text()); meta["version"] = "0.2.0"
        config.write_text(json.dumps(meta))
        self.edit_terms(lambda rows: rows.pop())
        refused = self.run_tool("release", self.project, expected=1)
        self.assertIn("withdraw", refused["error"])
        self.assertFalse((self.project / "releases" / "0.2.0").exists())

    def test_publication_preparation_is_a_reviewable_dry_run(self):
        self.run_tool("init", self.project, "--demo")
        self.run_tool("release", self.project)
        checkout = self.base / "w3id"
        (checkout / "ids").mkdir(parents=True)
        output = self.base / "publication"
        prepared = self.run_tool("prepare-publication", self.project, "--output", output, "--w3id-checkout", checkout)
        self.assertFalse(prepared["publication_performed"])
        self.assertFalse(prepared["registration_verified"])
        self.assertEqual(prepared["namespace_collision_check"], "checked_local_snapshot")
        namespace_dir = output / "w3id" / "ids" / "example-salmon-vocabulary"
        self.assertEqual({p.name for p in namespace_dir.iterdir()}, {".htaccess", "README.md"})
        rules = (namespace_dir / ".htaccess").read_text()
        self.assertNotIn("HTTP_ACCEPT", rules)
        self.assertNotIn("Options ", rules)
        self.assertIn("[R=303,L]", rules)
        workflow = (output / "vocabulary-pages.yml").read_text()
        self.assertIn("workflow_dispatch", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("push:", workflow)
        plan = json.loads((output / "http-checks.json").read_text())
        self.assertEqual(plan["execution_status"], "not_run")
        canonical = next(c for c in plan["checks"] if c["path"] == "concept/demo-observation")
        self.assertEqual(canonical["location"], "https://example-org.github.io/example-salmon-vocabulary/concept/demo-observation/")

    def test_namespace_collision_is_refused_including_case_variants(self):
        self.run_tool("init", self.project, "--demo")
        checkout = self.base / "w3id"
        (checkout / "ids" / "Example-Salmon-Vocabulary").mkdir(parents=True)
        refused = self.run_tool("validate", self.project, "--w3id-checkout", checkout, expected=1)
        self.assertIn("collision", refused["error"])

    def test_previews_cannot_be_written_inside_release_history(self):
        self.run_tool("init", self.project, "--demo")
        self.run_tool("release", self.project)
        output = self.project / "releases" / "publication-preview"
        refused = self.run_tool("prepare-publication", self.project, "--output", output, expected=1)
        self.assertIn("release history", refused["error"])
        self.assertFalse(output.exists())
        refused = self.run_tool("build", self.project, "--output", output, expected=1)
        self.assertIn("release history", refused["error"])
        self.assertFalse(output.exists())

    def test_same_version_cannot_be_rewritten_and_tampered_snapshot_is_refused(self):
        self.run_tool("init", self.project, "--demo")
        self.run_tool("release", self.project)
        self.assertTrue(self.run_tool("release", self.project)["unchanged"])
        self.edit_terms(lambda rows: rows[0].update(label="Renamed fictional label"))
        self.assertIn("new version", self.run_tool("release", self.project, expected=1)["error"])
        (self.project / "releases" / "0.1.0" / "concept" / "demo-observation" / "manifest.json").write_text("unexpected content")
        self.assertIn("hashes", self.run_tool("validate", self.project, expected=1)["error"])

    def test_definition_revision_needs_a_note_and_preserves_historical_bytes(self):
        self.run_tool("init", self.project, "--demo")
        self.run_tool("release", self.project)
        historical = self.project / "releases" / "0.1.0" / "vocabulary.ttl"
        original = historical.read_bytes()
        meta_path = self.project / "vocabulary.json"
        meta = json.loads(meta_path.read_text()); meta["version"] = "0.2.0"
        meta_path.write_text(json.dumps(meta))
        self.edit_terms(lambda rows: rows[0].update(definition="A clarified fictional definition."))
        self.assertIn("change_note", self.run_tool("release", self.project, expected=1)["error"])
        self.edit_terms(lambda rows: rows[0].update(change_note="Editorial clarification; reviewed meaning retained."))
        self.run_tool("release", self.project)
        self.assertEqual(historical.read_bytes(), original)
        new = json.loads((self.project / "releases" / "0.2.0" / "vocabulary.jsonld").read_text())
        self.assertIn("https://w3id.org/example-salmon-vocabulary/concept/demo-observation", [n["@id"] for n in new["@graph"]])

    def test_invalid_labels_hierarchy_replacements_and_ids_are_refused(self):
        self.run_tool("init", self.project, "--demo")
        original = (self.project / "concepts.csv").read_bytes()
        cases = [
            lambda rows: rows[0].update(alt_labels=rows[0]["label"]),
            lambda rows: rows[1].update(id=rows[0]["id"].upper()),
            lambda rows: rows[0].update(broader=rows[0]["id"]),
            lambda rows: (rows[0].update(broader=rows[1]["id"]), rows[1].update(broader=rows[0]["id"])),
            lambda rows: rows[0].update(replaced_by=rows[1]["id"]),
            lambda rows: rows[0].update(id="../../escape"),
            lambda rows: rows[0].update(source="javascript:alert(1)"),
            lambda rows: rows[0].update(definition=""),
        ]
        for index, change in enumerate(cases):
            with self.subTest(case=index):
                (self.project / "concepts.csv").write_bytes(original)
                self.edit_terms(change)
                self.run_tool("validate", self.project, expected=1)

    def test_publication_gate_refuses_demo_and_repository_mismatch(self):
        self.run_tool("init", self.project, "--demo")
        self.assertIn("fictional", self.run_tool("validate", self.project, "--for-publication", expected=1)["error"])
        self.assertIn("binding", self.run_tool("validate", self.project, "--repository", "other-owner/other-repo", expected=1)["error"])

    def test_config_mode_authors_a_project_and_rejects_malformed_source_iris(self):
        # Exercise the documented --config seam with invented contacts; passing
        # its metadata gate still establishes no external permission or truth.
        self.run_tool("init", self.project, "--demo")
        meta = json.loads((self.project / "vocabulary.json").read_text())
        del meta["example"]
        config = self.base / "metadata.json"
        config.write_text(json.dumps(meta))
        authored = self.base / "authored"
        self.run_tool("init", authored, "--config", config)
        self.assertIn("requires at least one", self.run_tool("validate", authored, expected=1)["error"])
        (authored / "concepts.csv").write_bytes((self.project / "concepts.csv").read_bytes())
        self.run_tool("validate", authored, "--for-publication", "--repository", "example-org/example-salmon-vocabulary")
        original = (self.project / "concepts.csv").read_bytes()
        for source in ("https://example.org/%zz", "https://example.org:invalid/source", "https://example.org:65536/source"):
            with self.subTest(source=source):
                (self.project / "concepts.csv").write_bytes(original)
                self.edit_terms(lambda rows: rows[0].update(source=source))
                self.run_tool("validate", self.project, expected=1)

    def test_website_escapes_author_text_and_all_relative_links_resolve(self):
        self.run_tool("init", self.project, "--demo")
        self.edit_terms(lambda rows: rows[0].update(label='Fictional <script>alert("x")</script> & category'))
        output = self.base / "website"
        self.run_tool("build", self.project, "--output", output)
        text = (output / "concept" / "demo-observation" / "index.html").read_text()
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        class Links(HTMLParser):
            def handle_starttag(inner, tag, attrs):
                for name, value in attrs:
                    if name == "href" and not value.startswith(("http:", "https:", "#")):
                        target = path.parent / value
                        self.assertTrue(target.exists(), f"broken local link {path}: {value}")
        for path in output.rglob("*.html"):
            Links().feed(path.read_text())

    def test_copied_tool_works_outside_the_plugin_checkout(self):
        self.run_tool("init", self.project, "--demo")
        proc = subprocess.run([sys.executable, str(self.project / "tools" / "controlled_vocabulary.py"), "build", str(self.project), "--output", str(self.base / "standalone")], cwd=self.base, text=True, capture_output=True, timeout=30, env=dict(os.environ, PYTHONPATH=str(self.base)))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["publication_performed"])


if __name__ == "__main__":
    unittest.main()
