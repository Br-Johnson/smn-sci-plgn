"""Offline transport controls with fake checkout bytes and subprocess receipts.

These do not run the private commons tools or establish scientific validity.
The root integration owner runs separate synthetic controls against the pin.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/commons-card/scripts/commons_card.py"
SPEC = importlib.util.spec_from_file_location("commons_card_controls", HELPER)
cc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cc)


class CommonsCardTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkout = self.root / "fake-checkout"
        self.workspace = self.root / "synthetic-bundle"
        self.checkout.mkdir()
        self.workspace.mkdir()
        self.card = self.workspace / "fake.card.md"
        self.ledger = self.workspace / "fake.ledger.json"
        self.card.write_text("synthetic card only\n", encoding="utf-8")
        self.ledger.write_text("[]\n", encoding="utf-8")
        self.hashes = {}
        for rel in cc.CLOSURE_HASHES:
            file = self.checkout / rel
            file.parent.mkdir(parents=True, exist_ok=True)
            data = ("synthetic code-surface control: " + rel).encode()
            file.write_bytes(data)
            self.hashes[rel] = hashlib.sha256(data).hexdigest()
        self.hash_patch = patch.object(cc, "CLOSURE_HASHES", self.hashes)
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)

    def invoke(self, action="validate", *options, receipt=None, git_head=None):
        args = [action, "--commons-checkout", str(self.checkout)]
        if action != "checklist":
            args += ["--workspace", str(self.workspace)]
        args += list(options)
        git = subprocess.CompletedProcess([], 0, f"{self.checkout}\n{git_head or cc.PIN}\n", "")
        receipt = receipt or subprocess.CompletedProcess([], 0, "synthetic findings\n", "synthetic warning\n")
        with patch.object(cc.subprocess, "run", side_effect=[git, receipt]) as run:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cc.main(args)
        return code, json.loads(out.getvalue()), run

    def test_validate_forces_pinned_schema_and_preserves_streams_and_failure(self):
        receipt = subprocess.CompletedProcess([], 1, '{"errors":["synthetic"]}\n', "warning\n")
        code, output, run = self.invoke(receipt=receipt)
        self.assertEqual(code, 1)
        self.assertEqual(output["returncode"], 1)
        self.assertEqual((output["stdout"], output["stderr"]), (receipt.stdout, receipt.stderr))
        self.assertEqual(output["output_kind"], "validation_findings")
        argv = run.call_args_list[1].args[0]
        self.assertEqual(argv[1:3], ["-I", "-B"])
        self.assertEqual(argv[3:], [str(self.checkout / "scripts/okf-check.py"), "--schema",
                                  str(self.checkout / "schema/concept.schema.json"), "--json", "--", str(self.workspace)])

    def test_preview_is_dry_run_without_report_and_not_validation(self):
        code, output, run = self.invoke("preview", "--card", self.card.name, "--ledger", self.ledger.name)
        self.assertEqual(code, 0)
        self.assertEqual(output["output_kind"], "ledger_preview")
        argv = run.call_args_list[1].args[0]
        self.assertIn("--dry-run", argv)
        self.assertNotIn("--report", argv)
        self.assertEqual(argv[-1], str(self.card))
        self.assertNotIn("ok", output)

    def test_check_is_explicit_from_card_and_never_checked_only(self):
        code, output, run = self.invoke("check", "--card", self.card.name)
        self.assertEqual(code, 0)
        self.assertEqual(output["output_kind"], "ledger_structure")
        self.assertEqual(run.call_args_list[1].args[0][3:],
                         [str(self.checkout / "scripts/ledger/ledger_check.py"), "--from-card", "--", str(self.card)])

    def test_repeated_cards_and_ledgers_preserve_order(self):
        second = self.workspace / "second.md"
        second.write_text("synthetic second card", encoding="utf-8")
        code, _, run = self.invoke("preview", "--card", second.name, "--card", self.card.name,
                                   "--ledger", self.ledger.name, "--ledger", self.ledger.name)
        self.assertEqual(code, 0)
        self.assertEqual(run.call_args_list[1].args[0][-3:], ["--", str(second), str(self.card)])
        self.assertEqual(run.call_args_list[1].args[0].count("--ledger"), 2)

    def test_checklist_verifies_closure_without_running_upstream(self):
        code, output, run = self.invoke("checklist")
        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(output["output_kind"], "contribution_checklist")
        self.assertIn("CONTRIBUTING.md", output["stdout"])
        self.assertIn("Never assert your own verification", output["stdout"])

    def test_wrong_pin_refuses_before_upstream(self):
        code, output, run = self.invoke(git_head="0" * 40)
        self.assertEqual(code, 2)
        self.assertEqual(output["error"], "commons checkout does not match the required pin")
        self.assertEqual(run.call_count, 1)

    def test_every_execution_and_governance_file_is_checked(self):
        for rel in self.hashes:
            with self.subTest(rel=rel):
                file = self.checkout / rel
                original = file.read_bytes()
                file.write_bytes(original + b"changed")
                code, _, run = self.invoke()
                self.assertEqual(code, 2)
                self.assertEqual(run.call_count, 1)
                file.write_bytes(original)

    def test_symlinked_closure_is_refused(self):
        file = self.checkout / "CONTRIBUTING.md"
        original = file.read_bytes()
        target = self.root / "synthetic-target"
        target.write_bytes(original)
        file.unlink()
        file.symlink_to(target)
        code, _, run = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(run.call_count, 1)

    def test_workspace_nested_symlink_is_refused_without_reading_target(self):
        (self.workspace / "nested.md").symlink_to(self.root / "missing-private-placeholder")
        code, _, run = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(run.call_count, 1)

    def test_card_escape_and_symlink_refused_before_upstream(self):
        link = self.workspace / "link.md"
        link.symlink_to(self.card)
        for card in ("../outside.md", str(self.root / "outside.md"), link.name):
            with self.subTest(card=card):
                code, _, run = self.invoke("check", "--card", card)
                self.assertEqual(code, 2)
                self.assertEqual(run.call_count, 1)

    def test_ledger_escape_refused_before_upstream(self):
        code, _, run = self.invoke("preview", "--card", self.card.name, "--ledger", "../outside.json")
        self.assertEqual(code, 2)
        self.assertEqual(run.call_count, 1)

    def test_workspace_may_not_overlap_checkout(self):
        for workspace in (self.checkout, self.root):
            with self.subTest(workspace=workspace):
                original = self.workspace
                self.workspace = workspace
                code, _, run = self.invoke()
                self.workspace = original
                self.assertEqual(code, 2)
                self.assertEqual(run.call_count, 1)

    def test_wrong_action_arguments_refuse(self):
        cases = [("preview", []), ("check", []), ("validate", ["--card", self.card.name]),
                 ("check", ["--card", self.card.name, "--ledger", self.ledger.name])]
        for action, options in cases:
            with self.subTest(action=action, options=options):
                code, _, run = self.invoke(action, *options)
                self.assertEqual(code, 2)
                self.assertLessEqual(run.call_count, 1)

    def test_missing_checkout_is_machine_readable_refusal(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = cc.main(["validate", "--commons-checkout", str(self.root / "missing-checkout"),
                            "--workspace", str(self.workspace)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["error"], "commons checkout must be an existing directory")

    def test_git_failure_does_not_run_upstream(self):
        with patch.object(cc.subprocess, "run", return_value=subprocess.CompletedProcess([], 128, "", "fake git failure")) as run:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = cc.main(["checklist", "--commons-checkout", str(self.checkout)])
        self.assertEqual(code, 2)
        self.assertEqual(run.call_count, 1)
        self.assertIn("error", json.loads(out.getvalue()))

    def test_unavailable_upstream_runtime_is_preserved(self):
        receipt = subprocess.CompletedProcess([], 1, "", "ModuleNotFoundError: synthetic dependency\n")
        code, output, _ = self.invoke(receipt=receipt)
        self.assertEqual(code, 1)
        self.assertEqual(output["stderr"], receipt.stderr)

    def test_arbitrary_report_flag_is_not_accepted(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                cc.main(["preview", "--commons-checkout", str(self.checkout), "--workspace", str(self.workspace),
                         "--card", self.card.name, "--ledger", self.ledger.name, "--report", "out.json"])
        self.assertEqual(raised.exception.code, 2)


class CommonsCardEvalFeasibilityTests(unittest.TestCase):
    def test_refusal_receipt_and_command_fit_deterministic_graders(self):
        # This runs only the helper's missing-checkout refusal. It neither runs
        # a model nor opens the synthetic card, much less a private real card.
        spec = importlib.util.spec_from_file_location("commons_eval_scaffold", ROOT / "scripts/validate_scaffold.py")
        vs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vs)
        fixture = ROOT / "evals/commons-card/fixtures"
        argv = [str(HELPER), "validate", "--commons-checkout", str(fixture / "missing-checkout"),
                "--workspace", str(fixture / "bundle")]
        result = subprocess.run([sys.executable, "-I", "-B", *argv],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertIn("error", receipt)
        self.assertNotIn("stdout", receipt)
        graders = ROOT / "evals/commons-card/graders"
        for name in ("refusal-reported", "pin-reported"):
            fields, _ = vs.read_eval_file(graders / f"{name}.md")
            flags = re.IGNORECASE if "i" in fields.get("flags", "") else 0
            self.assertRegex(result.stdout, re.compile(fields["pattern"], flags))
        fields, _ = vs.read_eval_file(graders / "adapter-called.md")
        self.assertRegex(json.dumps({"command": "python3 " + " ".join(argv)}), fields["input_match"])
        fields, _ = vs.read_eval_file(graders / "skill-fired.md")
        self.assertRegex("commons-card", fields["input_match"])


if __name__ == "__main__":
    unittest.main()
