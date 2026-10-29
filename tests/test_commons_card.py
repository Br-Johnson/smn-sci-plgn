"""Tests for the commons-card adapter.

The offline tests build a small git clone of their own, with stand-in scripts
in the commons' layout, and pin the adapter to its first commit. They prove the
plumbing: which copy runs, with which arguments, from which directory, what
the response carries, and that nothing is left behind. They run anywhere, with
plain ``python3``.

The live tests run the real commons' scripts at the real pin, through uv, and
use the commons' own ledger control cards as positive and negative controls.
The commons is private, so they run only where ``SALMON_COMMONS_DIR`` names a
clone of it and uv is installed; CI skips them. That skip retires if the
commons becomes public, when CI could clone it.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = REPO_ROOT / "skills" / "commons-card" / "scripts" / "commons_card.py"

spec = importlib.util.spec_from_file_location("commons_card", ADAPTER)
commons_card = importlib.util.module_from_spec(spec)
spec.loader.exec_module(commons_card)

LIVE_CLONE = os.environ.get("SALMON_COMMONS_DIR")
LIVE = bool(LIVE_CLONE) and shutil.which("uv") is not None

# Stand-ins for the commons' scripts. Each says which copy ran and with what,
# so a test can tell the pinned copy from the clone's own.
VALIDATOR = """\
import json, os, sys
print(json.dumps({"copy": "pinned", "argv": sys.argv[1:], "cwd": os.getcwd(), "errors": []}))
"""
TABLE_WRITER = """\
import json, sys
HEADING = "## Citation ledger"
if __name__ == "__main__":
    args = sys.argv[1:]
    report = args[args.index("--report") + 1]
    cards = [a for a in args if a.endswith(".md")]
    for card in cards:
        if "--dry-run" in args:
            print(HEADING)
        else:
            with open(card, "a", encoding="utf-8") as handle:
                handle.write("\\n" + HEADING + "\\n")
    with open(report, "w", encoding="utf-8") as handle:
        json.dump({"argv": args, "cards": cards}, handle)
"""
CARD_CHECK = """\
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger_table import HEADING  # the real check imports the table writer from beside it
failed = 0
for card in [a for a in sys.argv[1:] if not a.startswith("--")]:
    bad = "BAD" in open(card, encoding="utf-8").read()
    print(("FAIL" if bad else "ok") + "  " + card + "  " + " ".join(sys.argv[1:]))
    failed += bad
sys.exit(1 if failed else 0)
"""
CHECKLIST = "# Contributing\n\nA stand-in written for the plugin's tests.\n"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.org", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def build_clone(root: Path) -> str:
    """A git clone in the commons' layout, with one commit; returns its SHA."""
    files = {
        "scripts/okf-check.py": VALIDATOR,
        "scripts/ledger/ledger_table.py": TABLE_WRITER,
        "scripts/ledger/ledger_check.py": CARD_CHECK,
        "schema/concept.schema.json": "{}\n",
        "CONTRIBUTING.md": CHECKLIST,
        "concepts/good.md": "---\ntype: Concept\n---\nA card.\n",
        "concepts/bad.md": "---\ntype: Concept\n---\nBAD card.\n",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "stand-in commons")
    return git(root, "rev-parse", "HEAD")


@contextlib.contextmanager
def working_directory(path: Path):
    before = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


class OfflineAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.clone = (base / "commons").resolve()
        self.clone.mkdir()
        self.pin = build_clone(self.clone)
        # Every temporary directory the adapter makes lands here, so a test can
        # see that it is gone again.
        self.scratch = base / "scratch"
        self.scratch.mkdir()
        patcher = mock.patch.object(tempfile, "tempdir", str(self.scratch))
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SALMON_COMMONS_DIR", None)

    def call(self, **request) -> dict:
        request.setdefault("commons_dir", str(self.clone))
        response = commons_card.handle(request, pin=self.pin)
        self.assertEqual(list(self.scratch.iterdir()), [], "the adapter left its copies behind")
        return response

    def test_runtime_reports_the_clone_and_the_pin(self) -> None:
        response = self.call(action="runtime")
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["pin"]["commit"], self.pin)
        self.assertEqual(response["checkout"]["path"], str(self.clone))
        self.assertEqual(response["checkout"]["found_by"], "commons_dir")
        self.assertEqual(response["checkout"]["head"], self.pin)
        self.assertTrue(response["checkout"]["contains_pin"])
        self.assertEqual(response["checkout"]["drift"], [])
        self.assertEqual(set(response["dependencies"]), {"pyyaml", "jsonschema"})

    def test_the_clone_is_found_from_the_environment_then_the_working_directory(self) -> None:
        nested = self.clone / "concepts"
        os.environ["SALMON_COMMONS_DIR"] = str(nested)
        response = commons_card.handle({"action": "runtime"}, pin=self.pin)
        self.assertEqual(response["checkout"]["found_by"], "SALMON_COMMONS_DIR")
        self.assertEqual(response["checkout"]["path"], str(self.clone))
        del os.environ["SALMON_COMMONS_DIR"]
        with working_directory(nested):
            response = commons_card.handle({"action": "runtime"}, pin=self.pin)
        self.assertEqual(response["checkout"]["found_by"], "the working directory")
        self.assertEqual(response["checkout"]["path"], str(self.clone))

    def test_validate_refuses_changed_rules_instead_of_reporting_a_historical_pass(self) -> None:
        (self.clone / "scripts" / "okf-check.py").write_text(
            'print(\'{"copy": "clone"}\')\n', encoding="utf-8"
        )
        response = self.call(action="validate")
        self.assertFalse(response["ok"], response)
        self.assertEqual(response["error"]["code"], "upstream_drift")
        self.assertNotIn("ran", response)
        self.assertEqual(response["checkout"]["drift"], ["scripts/okf-check.py"])
        self.assertEqual(response["pin"]["commit"], self.pin)
        inspected = self.call(action="runtime")
        self.assertTrue(inspected["ok"], inspected)
        self.assertEqual(inspected["checkout"]["drift"], ["scripts/okf-check.py"])

    def test_validate_gaps_asks_for_the_gap_register(self) -> None:
        response = self.call(action="validate", gaps=True)
        self.assertEqual(response["output"]["argv"][:2], [".", "--gaps"])

    def test_ledger_table_dry_run_changes_no_card(self) -> None:
        ledger = Path(self._tmp.name) / "ledger.json"
        ledger.write_text('{"rows": []}', encoding="utf-8")
        before = (self.clone / "concepts" / "good.md").read_text(encoding="utf-8")
        response = self.call(
            action="ledger_table",
            cards=[str(self.clone / "concepts" / "good.md")],
            ledgers=[str(ledger)],
        )
        self.assertTrue(response["ok"], response)
        self.assertFalse(response["write"])
        self.assertEqual(response["stdout"], "## Citation ledger\n")
        self.assertEqual((self.clone / "concepts" / "good.md").read_text(encoding="utf-8"), before)
        # An absolute card path reaches the script relative to the clone's root,
        # as the commons' own commands pass it.
        self.assertEqual(response["report"]["cards"], ["concepts/good.md"])
        self.assertIn("--dry-run", response["report"]["argv"])
        self.assertEqual(response["ran"]["args"][:2], ["--ledger", str(ledger.resolve())])
        self.assertEqual(response["ran"]["args"][2:4], ["--report", "<scratch>/report.json"])

    def test_ledger_table_writes_only_when_asked(self) -> None:
        ledger = Path(self._tmp.name) / "ledger.json"
        ledger.write_text('{"rows": []}', encoding="utf-8")
        response = self.call(action="ledger_table", cards=["concepts/good.md"], ledgers=[str(ledger)], write=True)
        self.assertTrue(response["ok"], response)
        self.assertTrue(response["write"])
        self.assertNotIn("--dry-run", response["report"]["argv"])
        self.assertTrue((self.clone / "concepts" / "good.md").read_text(encoding="utf-8").endswith("## Citation ledger\n"))

    def test_ledger_table_refuses_paths_it_cannot_use(self) -> None:
        ledger = Path(self._tmp.name) / "ledger.json"
        ledger.write_text('{"rows": []}', encoding="utf-8")
        outside = Path(self._tmp.name) / "elsewhere.md"
        outside.write_text("---\n---\n", encoding="utf-8")
        cases = (
            ({"cards": [str(outside)], "ledgers": [str(ledger)]}, "outside_checkout"),
            ({"cards": ["../elsewhere.md"], "ledgers": [str(ledger)]}, "outside_checkout"),
            ({"cards": ["concepts/missing.md"], "ledgers": [str(ledger)]}, "missing_file"),
            ({"cards": ["concepts/good.md"], "ledgers": ["missing.json"]}, "missing_file"),
            ({"cards": "concepts/good.md", "ledgers": [str(ledger)]}, "invalid_input"),
            ({"cards": ["concepts/good.md"], "ledgers": []}, "invalid_input"),
            ({"cards": ["concepts/good.md"], "ledgers": [str(ledger)], "write": "yes"}, "invalid_input"),
        )
        for request, code in cases:
            with self.subTest(request=request):
                response = self.call(action="ledger_table", **request)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], code)

    def test_check_card_runs_beside_the_table_writer_and_reports_failure(self) -> None:
        response = self.call(action="check_card", cards=["concepts/good.md", "concepts/bad.md"], checked_only=True)
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "nonzero_exit")
        self.assertEqual(response["exit_code"], 1)
        self.assertIn("ok  concepts/good.md  --from-card --checked-only", response["stdout"])
        self.assertIn("FAIL  concepts/bad.md", response["stdout"])

    def test_checklist_is_the_pinned_text_and_says_when_the_clone_differs(self) -> None:
        response = self.call(action="checklist")
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["text"], CHECKLIST)
        self.assertFalse(response["differs_in_checkout"])
        (self.clone / "CONTRIBUTING.md").write_text("# Changed\n", encoding="utf-8")
        response = self.call(action="checklist")
        self.assertEqual(response["text"], CHECKLIST)
        self.assertTrue(response["differs_in_checkout"])

    def test_a_clone_without_the_pin_is_refused(self) -> None:
        response = commons_card.handle({"action": "validate", "commons_dir": str(self.clone)})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "pin_missing")
        self.assertIn("fetch origin main", response["error"]["message"])
        self.assertEqual(response["pin"]["commit"], commons_card.COMMONS_PIN)

    def test_a_directory_outside_any_clone_is_refused(self) -> None:
        response = self.call(action="runtime", commons_dir=str(self.scratch))
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "no_checkout")
        self.assertIn("SALMON_COMMONS_DIR", response["error"]["message"])

    def test_an_unknown_action_is_refused(self) -> None:
        response = self.call(action="publish")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_action")

    def test_the_command_line_answers_in_json(self) -> None:
        run = subprocess.run(
            [sys.executable, str(ADAPTER)],
            input=json.dumps({"action": "runtime", "commons_dir": str(self.clone)}),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        response = json.loads(run.stdout)
        self.assertEqual(response["error"]["code"], "pin_missing")
        run = subprocess.run([sys.executable, str(ADAPTER)], input="", capture_output=True, text=True, timeout=60)
        self.assertEqual(json.loads(run.stdout)["error"]["code"], "invalid_input")


class NoCommonsFilesShippedTests(unittest.TestCase):
    """The plugin ships none of the commons' scripts or rules (tern SPEC K1-4, PL-5).

    Catches a copy of the commons' scripts or CONTRIBUTING.md committed under
    its own name anywhere outside .git. Misses content copied under another
    name or pasted into prose. Retires when tern's package-data scan of the
    plugin build (SPEC K1-4) covers this repository.
    """

    def test_no_commons_script_is_vendored(self) -> None:
        names = {"okf-check.py", "ledger_table.py", "ledger_check.py"}
        found = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in REPO_ROOT.rglob("*")
            if path.name in names and ".git" not in path.parts
        ]
        self.assertEqual(found, [])
        self.assertFalse((REPO_ROOT / "skills" / "commons-card" / "CONTRIBUTING.md").exists())


@unittest.skipUnless(LIVE, "set SALMON_COMMONS_DIR to a clone of the commons, with uv installed, to run")
class LiveCommonsTests(unittest.TestCase):
    """The real scripts at the real pin, against a real clone, through uv."""

    def run_adapter(self, request: dict) -> dict:
        request = {"commons_dir": LIVE_CLONE, **request}
        run = subprocess.run(
            ["uv", "run", "-q", str(ADAPTER)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    @contextlib.contextmanager
    def synthetic_bundle(self, writer: str, verifier: str | None):
        """Use authorized tools with synthetic cards, leaving the source clone untouched."""
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "commons"
            subprocess.run(
                ["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", LIVE_CLONE, str(clone)],
                capture_output=True, text=True, check=True,
            )
            git(clone, "checkout", "HEAD", "--", "scripts", "schema", "CONTRIBUTING.md")
            (clone / "concepts").mkdir()
            (clone / "index.md").write_text('---\nokf_version: "0.2"\n---\n\n# Synthetic controls\n')
            card = {
                "type": "Concept", "title": "Synthetic provenance control",
                "description": "A synthetic adapter integration fixture.",
                "status": "draft", "context": "data-informatics",
                "generated": {"by": writer, "at": "2026-10-29T00:00:00Z"},
                "sources": [{"id": "fixture", "resource": "https://example.org/source", "title": "Synthetic source"}],
                "alignment": {"related": ["https://example.org/term"]},
            }
            if verifier is not None:
                card["verified"] = [{"by": verifier, "at": "2026-10-29T00:00:00Z"}]
            (clone / "concepts" / "control.md").write_text(
                "---\n" + json.dumps(card) + "\n---\n\nSynthetic fixture claim.[^fixture]\n\n[^fixture]: Synthetic source.\n",
                encoding="utf-8",
            )
            yield clone

    def test_synthetic_provenance_is_checked_against_current_commons_rules(self) -> None:
        cases = (
            ("unverified-agent", "test-agent/1", None, None),
            ("independent-human", "human:synthetic-writer", "human:synthetic-reader", None),
            ("self-verification", "human:synthetic-writer", "human:synthetic-writer", "cannot verify their own card"),
            ("agent-verification", "human:synthetic-writer", "process:synthetic-checker", "names an agent/process"),
        )
        for name, writer, verifier, error in cases:
            with self.subTest(name=name), self.synthetic_bundle(writer, verifier) as clone:
                response = self.run_adapter({"action": "validate", "commons_dir": str(clone)})
                if error is None:
                    self.assertTrue(response["ok"], response)
                    self.assertEqual(response["output"]["errors"], [])
                else:
                    self.assertFalse(response["ok"], response)
                    self.assertEqual(response["error"]["code"], "nonzero_exit")
                    self.assertTrue(any(error in item["message"] for item in response["output"]["errors"]), response)

    def test_current_rule_drift_blocks_checks_and_ledger_writes_through_the_cli(self) -> None:
        with self.synthetic_bundle("test-agent/1", None) as clone:
            rules = clone / "CONTRIBUTING.md"
            rules.write_text(rules.read_text(encoding="utf-8") + "\nSynthetic changed contribution rule.\n")
            card = clone / "concepts" / "control.md"
            before = card.read_bytes()
            with tempfile.TemporaryDirectory() as tmp:
                ledger = Path(tmp) / "ledger.json"
                ledger.write_text('{"rows": []}', encoding="utf-8")
                requests = (
                    {"action": "validate"},
                    {"action": "check_card", "cards": ["concepts/control.md"]},
                    {"action": "ledger_table", "cards": ["concepts/control.md"], "ledgers": [str(ledger)], "write": True},
                )
                for request in requests:
                    with self.subTest(action=request["action"]):
                        response = self.run_adapter({"commons_dir": str(clone), **request})
                        self.assertFalse(response["ok"], response)
                        self.assertEqual(response["error"]["code"], "upstream_drift")
                        self.assertEqual(response["checkout"]["drift"], ["CONTRIBUTING.md"])
                        self.assertNotIn("ran", response)
                        self.assertEqual(card.read_bytes(), before)

    def test_runtime_is_ready(self) -> None:
        response = self.run_adapter({"action": "runtime"})
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["dependencies"], {"jsonschema": True, "pyyaml": True})

    def test_validate_returns_the_validators_findings(self) -> None:
        response = self.run_adapter({"action": "validate"})
        self.assertIn(response["exit_code"], (0, 1), response.get("stderr"))
        self.assertTrue({"concepts", "gaps", "errors", "warnings"} <= set(response["output"]))
        self.assertGreater(response["output"]["concepts"], 0)

    def test_check_card_passes_and_fails_the_commons_own_controls(self) -> None:
        controls = "scripts/ledger/controls"
        passing = self.run_adapter({"action": "check_card", "cards": [f"{controls}/card-ok.card.txt"]})
        self.assertTrue(passing["ok"], passing)
        failing = self.run_adapter({"action": "check_card", "cards": [f"{controls}/card-missing-row.card.txt"]})
        self.assertFalse(failing["ok"])
        self.assertIn("no row in the in-card ledger", failing["stdout"])

    def test_ledger_table_dry_run_writes_the_section_and_leaves_the_clone_alone(self) -> None:
        card = "scripts/ledger/controls/card-ok.card.txt"
        rows = [
            {"source_id": "src-a", "url": "https://example.org/a", "resolution_status": "resolved",
             "resolution_method": "http-fetch, title_match=true", "fulltext_obtained": True,
             "passage_located": True, "passage_section_or_page": "p. 12", "checked_at": "2026-10-15",
             "checked_by": "the plugin's live test"},
            {"source_id": "src-b", "doi": "10.0000/b", "resolution_status": "resolved",
             "resolution_method": "CrossRef", "fulltext_obtained": False, "passage_located": False,
             "checked_at": "2026-10-15", "checked_by": "the plugin's live test"},
        ]
        before = subprocess.run(["git", "-C", LIVE_CLONE, "status", "--porcelain", "--", card],
                                capture_output=True, text=True, check=True).stdout
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.json"
            ledger.write_text(json.dumps({"rows": rows}), encoding="utf-8")
            response = self.run_adapter({"action": "ledger_table", "cards": [card], "ledgers": [str(ledger)]})
        self.assertTrue(response["ok"], response)
        self.assertTrue(response["stdout"].startswith("## Citation ledger"), response["stdout"])
        self.assertIn("`src-a`", response["stdout"])
        self.assertIn("`src-b`", response["stdout"])
        self.assertEqual(response["report"]["cards"]["card-ok.card.txt"]["rows"], 2)
        after = subprocess.run(["git", "-C", LIVE_CLONE, "status", "--porcelain", "--", card],
                               capture_output=True, text=True, check=True).stdout
        self.assertEqual(after, before)

    def test_checklist_is_contributing_at_the_pin(self) -> None:
        response = self.run_adapter({"action": "checklist"})
        self.assertTrue(response["ok"], response)
        self.assertTrue(response["text"].startswith("# Contributing"))


if __name__ == "__main__":
    unittest.main()
