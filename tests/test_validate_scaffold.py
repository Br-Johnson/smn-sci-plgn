"""The validator's plugin checks must fail on the drift they exist to catch.

Each test copies the repository to a temporary directory, plants one violation,
and asserts that the matching check rejects it. A guard that has never been
seen to fail is a claim, not a check, so every new check has a failing case
here next to the passing one.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_scaffold as vs  # noqa: E402

IGNORED = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store")

# Built from parts so that this file does not itself trip the scans it tests.
RETIRED_SKILL = "smn-ontology" + "-skill"
RETIRED_DFO_SKILL = "gcdfo-ontology" + "-skill"
RETIRED_FORK = "dfo-pacific-science" + "/metasalmon"


def skill_names(root: Path) -> list[str]:
    return sorted(path.name for path in (root / "skills").iterdir() if path.is_dir())


class PluginChecksTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        shutil.copytree(REPO_ROOT, self.root, ignore=IGNORED)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def edit_json(self, relative: str, change) -> None:
        path = self.root / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def edit_text(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assert_rejected(self, check, *args, fragment: str) -> None:
        with self.assertRaises(SystemExit) as caught:
            check(*args)
        self.assertIn(fragment, str(caught.exception))

    def test_current_repository_passes(self) -> None:
        names = skill_names(self.root)
        vs.validate_manifests(self.root)
        vs.validate_skill_frontmatter(self.root, names)
        vs.validate_skill_references(self.root, names)
        vs.check_package_pins(self.root)
        vs.check_no_local_term_search(self.root)

    # Manifests ---------------------------------------------------------------

    def test_manifest_version_drift_is_rejected(self) -> None:
        self.edit_json(".claude-plugin/plugin.json", lambda data: data.update(version="9.9.9"))
        self.assert_rejected(vs.validate_manifests, self.root, fragment="disagree on 'version'")

    def test_claude_manifest_adding_skill_directories_is_rejected(self) -> None:
        self.edit_json(".claude-plugin/plugin.json", lambda data: data.update(skills=["./extra-skills/"]))
        self.assert_rejected(vs.validate_manifests, self.root, fragment="must not declare 'skills'")

    def test_claude_only_component_directory_is_rejected(self) -> None:
        (self.root / "commands").mkdir()
        self.assert_rejected(vs.validate_manifests, self.root, fragment="commands at the plugin root")

    def test_marketplace_version_is_rejected(self) -> None:
        self.edit_json(
            ".claude-plugin/marketplace.json",
            lambda data: data["plugins"][0].update(version="0.0.1"),
        )
        self.assert_rejected(vs.validate_manifests, self.root, fragment="must not set version")

    # Skill names and references -----------------------------------------------

    def test_frontmatter_name_mismatch_is_rejected(self) -> None:
        self.edit_text("skills/salmon-terms/SKILL.md", "name: salmon-terms", "name: salmon-term-search")
        self.assert_rejected(
            vs.validate_skill_frontmatter,
            self.root,
            skill_names(self.root),
            fragment="must equal the directory name",
        )

    def test_reference_to_a_retired_skill_path_is_rejected(self) -> None:
        with (self.root / "docs" / "entrypoints.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\n- Shared ontology lookup: `skills/{RETIRED_SKILL}/SKILL.md`\n")
        self.assert_rejected(
            vs.validate_skill_references,
            self.root,
            skill_names(self.root),
            fragment=f"skills/{RETIRED_SKILL}/ does not exist",
        )

    def test_selector_naming_a_missing_skill_is_rejected(self) -> None:
        self.edit_text(
            "scripts/skill_graph_selector.py",
            '"lane:ontology-semantic-resolution": ("salmon-terms",),',
            f'"lane:ontology-semantic-resolution": ("{RETIRED_DFO_SKILL}",),',
        )
        self.assert_rejected(
            vs.validate_skill_references,
            self.root,
            skill_names(self.root),
            fragment="skill_graph_selector.py names skills that do not exist",
        )

    def test_history_file_may_name_retired_skills(self) -> None:
        # kb/log.md records the retirement, so it names the retired skills.
        text = (self.root / "kb" / "log.md").read_text(encoding="utf-8")
        self.assertIn(RETIRED_SKILL, text)
        vs.validate_skill_references(self.root, skill_names(self.root))

    # Package pins -----------------------------------------------------------------

    def test_pin_drift_in_one_adapter_is_rejected(self) -> None:
        self.edit_text(
            "skills/salmon-terms/scripts/salmon_terms.py",
            "metasalmonpy@v0.5.0",
            "metasalmonpy@v0.4.0",
        )
        self.assert_rejected(vs.check_package_pins, self.root, fragment="package pins disagree")

    def test_reference_to_the_retired_fork_is_rejected(self) -> None:
        with (self.root / "README.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\nSee https://github.com/{RETIRED_FORK} for details.\n")
        self.assert_rejected(vs.check_package_pins, self.root, fragment="retired metasalmon fork")

    def test_adapter_without_script_block_is_rejected(self) -> None:
        path = self.root / "skills" / "metasalmon-skill" / "scripts" / "metasalmon_api.py"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.split("# ///\n", 2)[-1], encoding="utf-8")
        self.assert_rejected(vs.check_package_pins, self.root, fragment="no PEP 723 script block")

    # Term search ---------------------------------------------------------------------

    def test_skill_script_reading_published_jsonld_is_rejected(self) -> None:
        script = self.root / "skills" / "salmon-terms" / "scripts" / "local_lookup.py"
        script.write_text(
            'URL = "https://salmon-data-mobilization.github.io/salmon-domain-ontology/smn.jsonld"\n',
            encoding="utf-8",
        )
        self.assert_rejected(vs.check_no_local_term_search, self.root, fragment="contains '.jsonld'")

    def test_shared_script_defining_its_own_search_is_rejected(self) -> None:
        (self.root / "scripts" / "term_helper.py").write_text(
            "def search_terms(data, query):\n    return [item for item in data if query in item]\n",
            encoding="utf-8",
        )
        self.assert_rejected(vs.check_no_local_term_search, self.root, fragment="defines search_terms()")

    def test_label_predicate_parsing_is_rejected(self) -> None:
        (self.root / "skills" / "rmis-skill" / "scripts" / "labels.py").write_text(
            'LABEL = "http://www.w3.org/2000/01/rdf-schema#label"\n',
            encoding="utf-8",
        )
        self.assert_rejected(vs.check_no_local_term_search, self.root, fragment="rdf-schema#label")

    # Eval cases ------------------------------------------------------------------------

    def assert_evals_rejected(self, fragment: str) -> None:
        self.assert_rejected(vs.validate_evals, self.root, skill_names(self.root), fragment=fragment)

    def test_current_evals_pass(self) -> None:
        stats = vs.validate_evals(self.root, skill_names(self.root))
        self.assertEqual(stats["cases"], len(skill_names(self.root)))

    def test_eval_prompt_with_an_unknown_key_is_rejected(self) -> None:
        self.edit_text("evals/rmis-skill/prompt.md", "tags: [smoke]", "tags: [smoke]\nengine: r")
        self.assert_evals_rejected("unknown frontmatter keys ['engine']")

    def test_eval_naming_a_retired_skill_is_rejected(self) -> None:
        self.edit_text("evals/salmon-terms/graders/skill-fired.md", "salmon-terms", RETIRED_SKILL)
        self.assert_evals_rejected("must name exactly one existing skill, and it names none")

    def test_eval_naming_a_missing_script_is_rejected(self) -> None:
        self.edit_text(
            "evals/salmon-terms/graders/adapter-called.md",
            r"salmon_terms\.py",
            r"smn_ontology_lookup\.py",
        )
        self.assert_evals_rejected("names a script the plugin does not ship")

    def test_skill_without_an_eval_is_rejected(self) -> None:
        shutil.rmtree(self.root / "evals" / "dart-query-skill")
        self.assert_evals_rejected("skills with no eval case: ['dart-query-skill']")

    def test_unknown_grader_type_is_rejected(self) -> None:
        self.edit_text("evals/npafc-skill/graders/results-summarised.md", "type: llm", "type: judge")
        self.assert_evals_rejected("type must be one of")

    def test_grader_expecting_a_tool_the_case_does_not_allow_is_rejected(self) -> None:
        self.edit_text(
            "evals/dart-query-skill/prompt.md",
            "allowed_tools: [Read, Glob, Grep, Skill, Bash]",
            "allowed_tools: [Read, Glob, Grep, Skill]",
        )
        self.assert_evals_rejected("expects Bash but evals/dart-query-skill/prompt.md does not allow it")

    def test_rubric_naming_a_missing_skill_is_rejected(self) -> None:
        self.edit_text(
            "evals/salmon-research-router-skill/graders/route-quality.md",
            "such as streamnet-api-skill",
            f"such as {RETIRED_SKILL}",
        )
        self.assert_evals_rejected("criteria name skills that do not exist")

    def test_unignored_eval_results_are_rejected(self) -> None:
        self.edit_text(".gitignore", "evals/results/\n", "")
        self.assert_evals_rejected("must ignore evals/results/")

    def test_out_of_range_run_limit_is_rejected(self) -> None:
        self.edit_text("evals/ptagis-skill/prompt.md", "max_turns: 12", "max_turns: 9999")
        self.assert_evals_rejected("max_turns must be an integer from 1 to 200")


class EvalFrontmatterParserTests(unittest.TestCase):
    """The small YAML subset the eval files are read with."""

    def parse(self, value: str):
        return vs.parse_yaml_scalar(vs._strip_yaml_comment(value), "test")

    def test_values_and_trailing_comments(self) -> None:
        self.assertEqual(self.parse("'a''b' # note"), "a'b")
        self.assertEqual(self.parse("'#kept' # dropped"), "#kept")
        self.assertEqual(self.parse('"x # kept" # dropped'), "x # kept")
        self.assertEqual(self.parse("[Read, Bash] # tools"), ["Read", "Bash"])
        self.assertEqual(self.parse("{ source: file, path: brief.md }"), {"source": "file", "path": "brief.md"})
        self.assertEqual(self.parse("plain words # comment"), "plain words")
        self.assertEqual(self.parse("12"), 12)
        self.assertIsNone(self.parse("# only a comment"))

    def test_constructs_outside_the_subset_are_rejected(self) -> None:
        for value in ("|", ">-", "&anchor value", "'unterminated"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                self.parse(value)


if __name__ == "__main__":
    unittest.main()
