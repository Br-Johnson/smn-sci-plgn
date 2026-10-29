from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.skill_graph_selector import select_graph_decision


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "skill_graph_selector_cases.json"
SCRIPT_PATH = REPO_ROOT / "scripts" / "skill_graph_selector.py"


class SkillGraphSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_backed_route_selection(self) -> None:
        self.assertGreaterEqual(len(self.cases), 20)
        for case in self.cases:
            with self.subTest(request=case["request"]):
                result = select_graph_decision(case["request"], repo_root=REPO_ROOT)
                expected = case["expected"]

                self.assertEqual(result["seeded_lanes"], expected["seeded_lanes"])
                self.assertEqual(result["selected_skills"], expected["selected_skills"])
                self.assertEqual(result["blocked_skills"], expected["blocked_skills"])
                self.assertEqual(result["unsupported_lanes"], expected["unsupported_lanes"])

                reasons = "\n".join(result["reasons"])
                for fragment in expected["reason_contains"]:
                    self.assertIn(fragment, reasons)

    def test_interpretation_routes_to_authorized_commons_but_contribution_does_not(self):
        script=SCRIPT_PATH
        def route(question):
            proc=subprocess.run([sys.executable,str(script),'--request',question],text=True,capture_output=True,check=True)
            return json.loads(proc.stdout)
        self.assertIn('commons-card',route('Interpret this research result using the Salmon Knowledge Commons')['selected_skills'])
        self.assertIn('commons-card',route('Search the Commons for winter evidence')['selected_skills'])
        self.assertNotIn('commons-card',route('Contribute a Commons card')['selected_skills'])


    def test_cli_emits_json(self) -> None:
        case = self.cases[0]
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--request", case["request"]],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["seeded_lanes"], case["expected"]["seeded_lanes"])
        self.assertEqual(payload["selected_skills"], case["expected"]["selected_skills"])


if __name__ == "__main__":
    unittest.main()
