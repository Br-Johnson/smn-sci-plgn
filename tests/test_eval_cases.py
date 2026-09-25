"""Offline checks on the eval cases whose skills run without a network.

These tests do not run or score any eval case. Scoring one means a live model
run through `claude plugin eval`, which needs Claude Code 2.1.269 or later and
credentials. What these do instead is feed each deterministic grader (a regex
or a tool_used pattern, never an llm rubric) the output of the script its
skill runs, offline, so that a case cannot silently become impossible to pass
because the skill's output or the grader drifted.

Covered: salmon-stock-brief-workflow-skill, salmon-entity-normalizer-skill,
dart-query-skill (its catalog is built in), and salmon-research-router-skill.
The other nine cases need network access or a package install, so only the
structural checks in scripts/validate_scaffold.py reach them offline.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS = REPO_ROOT / "evals"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_scaffold as vs  # noqa: E402


def grader(case: str, name: str) -> dict:
    fields, body = vs.read_eval_file(EVALS / case / "graders" / f"{name}.md")
    fields["body"] = body
    return fields


def prompt(case: str) -> str:
    return vs.read_eval_file(EVALS / case / "prompt.md")[1]


def compiled(spec: dict, key: str = "pattern") -> re.Pattern:
    return re.compile(spec[key], re.IGNORECASE if "i" in (spec.get("flags") or "") else 0)


def run_script(path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(path), *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def bash_input(command: str) -> str:
    """The JSON-encoded Bash tool input that tool_used graders are matched against."""
    return json.dumps({"command": command})


class OfflineGraderFeasibilityTests(unittest.TestCase):
    def test_stock_brief_contract_satisfies_its_file_graders(self) -> None:
        case = "salmon-stock-brief-workflow-skill"
        helper = REPO_ROOT / "skills" / case / "scripts" / "stock_brief_contract.py"
        file_grader = grader(case, "brief-written")
        sections = grader(case, "contract-sections")
        self.assertEqual(sections["target"]["path"], file_grader["path"])
        self.assertIn(file_grader["path"], prompt(case))

        template = run_script(helper, "--template")
        self.assertEqual(template.returncode, 0, template.stderr)
        with tempfile.TemporaryDirectory() as workspace:
            brief = Path(workspace) / file_grader["path"]
            brief.write_text(template.stdout, encoding="utf-8")
            checked = run_script(helper, str(brief))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertRegex(brief.read_text(encoding="utf-8"), compiled(sections))

    def test_normalizer_output_satisfies_its_graders(self) -> None:
        case = "salmon-entity-normalizer-skill"
        quoted = re.search(r'"([^"]+)"', prompt(case))
        self.assertIsNotNone(quoted, "the case prompt quotes the request to normalize")
        result = run_script(
            REPO_ROOT / "skills" / case / "scripts" / "normalize_entities.py",
            stdin=json.dumps({"text": quoted.group(1)}),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("species-normalized", "unit-systems"):
            with self.subTest(grader=name):
                self.assertRegex(result.stdout, compiled(grader(case, name)))

    def test_dart_catalog_satisfies_its_graders(self) -> None:
        case = "dart-query-skill"
        result = run_script(
            REPO_ROOT / "skills" / case / "scripts" / "dart_query_catalog.py",
            stdin=json.dumps({"action": "catalog"}),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("paths-listed", "pit-page"):
            with self.subTest(grader=name):
                self.assertRegex(result.stdout, compiled(grader(case, name)))

    def test_router_route_includes_a_skill_its_rubric_accepts(self) -> None:
        case = "salmon-research-router-skill"
        from skill_graph_selector import select_graph_decision  # noqa: PLC0415

        decision = select_graph_decision(prompt(case), repo_root=REPO_ROOT)
        rubric_skills = set(re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*-skill\b", grader(case, "route-quality")["body"]))
        self.assertTrue(rubric_skills & set(decision["selected_skills"]), decision)

    def test_router_no_data_source_grader_covers_every_source_adapter(self) -> None:
        # The external-source skills are exactly the ones the skill-platform map
        # lists, so a new source skill that the grader does not cover fails here.
        spec = grader("salmon-research-router-skill", "no-data-source")
        self.assertEqual((spec["min"], spec["max"], spec["arm"]), (0, 0, "both"))
        pattern = compiled(spec, "input_match")
        mapping = vs.load_json(REPO_ROOT / "registry" / "skill-platform-map.json")
        sources = sorted(
            script
            for entry in mapping["skills"]
            for script in (REPO_ROOT / "skills" / entry["skill"] / "scripts").glob("*.py")
        )
        self.assertTrue(sources)
        for script in sources:
            with self.subTest(script=script.name):
                self.assertRegex(bash_input(f"python3 {script}"), pattern)
        for local in (
            REPO_ROOT / "scripts" / "skill_graph_selector.py",
            REPO_ROOT / "skills" / "salmon-entity-normalizer-skill" / "scripts" / "normalize_entities.py",
        ):
            with self.subTest(local=local.name):
                self.assertNotRegex(bash_input(f"python3 {local}"), pattern)


if __name__ == "__main__":
    unittest.main()
