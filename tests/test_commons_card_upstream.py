"""Opt-in offline controls against the private pinned tools, with fabricated inputs.

Set SMN_COMMONS_CHECKOUT to an already authorized checkout. These tests never
acquire it or inspect its real cards. Default CI exercises transport mocks in
test_commons_card.py; this separate profile proves the actual upstream commands.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "skills" / "commons-card" / "scripts" / "commons_card.py"
COMMONS = os.environ.get("SMN_COMMONS_CHECKOUT")
PIN = "1b7594e6263933e08ae196b4374373eb907c137f"

# Authored fiction: no imported source, card, scientific outcome or assertion.
CARD = """---
type: Concept
title: Fictional widget
description: A fabricated control for structural tooling only.
status: draft
context: data-informatics
generated:
  by: process:synthetic-control
  at: '2026-01-01T00:00:00Z'
sources:
  - id: fixture-source
    resource: https://example.invalid/fixture-record
    title: Fabricated fixture record
    author: Fixture Author
    published: '2026'
alignment:
  exact: [https://example.invalid/fictional-term]
---

A fictional widget is an invented test object.[^fixture-source]

{section}

[^fixture-source]: Fixture Author. Fabricated fixture record. p. 7.
"""

SECTION = """## Citation ledger

Checked synthetic records only; no human or citation verification.

| Source | Resolved by | Full text | Passage | Quote |
| --- | --- | --- | --- | --- |
| `fixture-source` | fixture local record | yes | p. 7 | |
"""


@unittest.skipUnless(COMMONS, "set SMN_COMMONS_CHECKOUT for private pinned-tool offline controls")
class PinnedCommonsControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.commons = Path(COMMONS).resolve()
        head = subprocess.check_output(
            ["git", "-C", str(cls.commons), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != PIN:
            raise AssertionError("supplied commons checkout is not the declared pin")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name) / "synthetic-bundle"
        self.workspace.mkdir()
        (self.workspace / "index.md").write_text(
            "---\nokf_version: '0.2'\n---\n\nSynthetic control bundle.\n", encoding="utf-8"
        )
        self.card = self.workspace / "fictional-widget.md"
        self.card.write_text(CARD.format(section=""), encoding="utf-8")
        self.ledger = self.workspace / "synthetic-ledger.json"
        self.ledger.write_text(json.dumps({
            "producer": "synthetic-control",
            "date": "2026-01-01",
            "rows": [{
                "source_id": "fixture-source",
                "resource": "https://example.invalid/fixture-record",
                "title": "Fabricated fixture record",
                "resolution_status": "resolved",
                "resolution_method": "fixture local record",
                "fulltext_obtained": True,
                "passage_located": True,
                "passage_section_or_page": "p. 7",
                "cards": ["fictional-widget"],
            }],
        }), encoding="utf-8")

    def snapshot(self) -> dict[str, str]:
        return {
            str(path.relative_to(self.workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.workspace.rglob("*") if path.is_file()
        }

    def call(self, action: str, *arguments: str) -> tuple[subprocess.CompletedProcess, dict]:
        before = self.snapshot()
        command = [sys.executable, "-I", "-B", str(ADAPTER), action,
                   "--commons-checkout", str(self.commons)]
        if action != "checklist":
            command += ["--workspace", str(self.workspace)]
        result = subprocess.run(command + list(arguments), cwd=self.temporary.name,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(before, self.snapshot(), "read-only command modified an input")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["pin"], PIN)
        self.assertTrue(payload["structural_only"])
        self.assertNotIn("verified", payload)
        self.assertNotIn("ok", payload)
        self.assertEqual(payload["returncode"], result.returncode)
        return result, payload

    def test_valid_draft_bundle_is_structurally_valid(self) -> None:
        result, payload = self.call("validate")
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["output_kind"], "validation_findings")
        json.loads(payload["stdout"])

    def test_unknown_frontmatter_key_is_rejected(self) -> None:
        text = self.card.read_text().replace("status: draft", "status: draft\ninvented_field: true")
        self.card.write_text(text, encoding="utf-8")
        result, payload = self.call("validate")
        self.assertEqual(result.returncode, 1, payload)
        self.assertIn("invented_field", payload["stdout"])

    def test_broken_footnote_is_rejected(self) -> None:
        text = self.card.read_text().replace("object.[^fixture-source]", "object.[^absent-source]")
        self.card.write_text(text, encoding="utf-8")
        result, payload = self.call("validate")
        self.assertEqual(result.returncode, 1, payload)

    def test_preview_generates_section_without_inserting_it(self) -> None:
        result, payload = self.call(
            "preview", "--card", self.card.name, "--ledger", self.ledger.name
        )
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["output_kind"], "ledger_preview")
        self.assertIn("## Citation ledger", payload["stdout"])
        self.assertNotIn("## Citation ledger", self.card.read_text())
        checked, findings = self.call("check", "--card", self.card.name)
        self.assertEqual(checked.returncode, 1, findings)
        self.assertIn("no in-card ledger", findings["stdout"] + findings["stderr"])

    def test_unresolved_preview_can_exit_zero_without_being_a_pass(self) -> None:
        ledger = json.loads(self.ledger.read_text())
        ledger["rows"][0]["resolution_status"] = "unresolved"
        self.ledger.write_text(json.dumps(ledger), encoding="utf-8")
        result, payload = self.call(
            "preview", "--card", self.card.name, "--ledger", self.ledger.name
        )
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["output_kind"], "ledger_preview")
        self.assertIn("unresolved", payload["stdout"])

    def test_explicit_card_check_validates_unmarked_card(self) -> None:
        self.card.write_text(CARD.format(section=SECTION), encoding="utf-8")
        result, payload = self.call("check", "--card", self.card.name)
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["output_kind"], "ledger_structure")

    def test_checked_only_skip_is_not_explicit_card_coverage(self) -> None:
        self.assertNotIn("citations_checked", self.card.read_text())
        explicit, payload = self.call("check", "--card", self.card.name)
        self.assertEqual(explicit.returncode, 1, payload)
        before = self.snapshot()
        skipped = subprocess.run([
            sys.executable, "-I", "-B", str(self.commons / "scripts/ledger/ledger_check.py"),
            "--from-card", "--checked-only", "--", str(self.card),
        ], capture_output=True, text=True, timeout=30)
        self.assertEqual(skipped.returncode, 0, skipped.stderr)
        self.assertIn("nothing to check", skipped.stdout)
        self.assertEqual(before, self.snapshot())

    def test_unresolved_table_row_is_rejected(self) -> None:
        section = SECTION.replace("fixture local record", "unresolved")
        self.card.write_text(CARD.format(section=section), encoding="utf-8")
        result, payload = self.call("check", "--card", self.card.name)
        self.assertEqual(result.returncode, 1, payload)
        self.assertIn("not resolved", payload["stdout"] + payload["stderr"])

    def test_duplicate_table_row_is_rejected(self) -> None:
        row = "| `fixture-source` | fixture local record | yes | p. 7 | |\n"
        self.card.write_text(CARD.format(section=SECTION + row), encoding="utf-8")
        result, payload = self.call("check", "--card", self.card.name)
        self.assertEqual(result.returncode, 1, payload)
        self.assertIn("more than one table row", payload["stdout"] + payload["stderr"])

    def test_unlocated_passage_is_rejected(self) -> None:
        self.card.write_text(CARD.format(section=SECTION.replace("p. 7", "not located")), encoding="utf-8")
        result, payload = self.call("check", "--card", self.card.name)
        self.assertEqual(result.returncode, 1, payload)
        self.assertIn("Passage says", payload["stdout"] + payload["stderr"])

    def test_mismatched_footnote_place_is_a_warning_not_entailment(self) -> None:
        self.card.write_text(CARD.format(section=SECTION.replace("p. 7", "p. 9")), encoding="utf-8")
        result, payload = self.call("check", "--card", self.card.name)
        self.assertEqual(result.returncode, 0, payload)
        self.assertIn("compare them", payload["stdout"] + payload["stderr"])

    def test_checklist_preserves_human_gates(self) -> None:
        result, payload = self.call("checklist")
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["output_kind"], "contribution_checklist")
        self.assertIn("CONTRIBUTING", payload["stdout"])
        self.assertIn("human", payload["stdout"].lower())


if __name__ == "__main__":
    unittest.main()
