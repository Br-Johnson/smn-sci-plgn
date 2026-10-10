"""Smoke tests for the two package adapters.

The offline test runs everywhere. It proves an adapter started with plain
``python3``, where metasalmonpy is not installed, answers with a JSON error
rather than a traceback, which also proves it imports nothing heavy at startup.

The live tests install metasalmonpy from its pinned tag through uv and call
it, so they need uv and network access. They include the review round trip
(a packet the package builds offline, answered and ingested through the
adapter) and the sdp-semantic-review skill's Theme A replay: its controls, and
the recorded cohort, which must still pass its oracles under the pinned
release. They run only when
``SMN_PLUGIN_LIVE_ADAPTERS=1``, which the CI workflow sets in its
package-adapters job, and the default offline suite skips them. That skip
retires if the adapters stop needing the network, for example if the package
were vendored or these tests moved to recorded responses.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SALMON_TERMS = REPO_ROOT / "skills" / "salmon-terms" / "scripts" / "salmon_terms.py"
METASALMON_API = REPO_ROOT / "skills" / "metasalmon-skill" / "scripts" / "metasalmon_api.py"
ADAPTERS = (SALMON_TERMS, METASALMON_API)
REPLAY = REPO_ROOT / "evals" / "sdp-semantic-review" / "replay_theme_a.py"
# A package and its review packet, built offline: a search that finds nothing
# leaves every shortlist empty, which the round trip handles like any other.
BUILD_PACKET = """
import json, sys, warnings
import pandas as pd
import metasalmonpy as ms

frame = pd.DataFrame({"stream": ["Goldstream", "Sooke"], "spawner_count": [120, 45]})
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ms.create_sdp(frame, sys.argv[1], dataset_id="demo-1", seed_semantics=False, check_updates=False)
    built = ms.write_semantic_review_packet(sys.argv[1], search_fn=lambda *a, **k: pd.DataFrame(), quiet=True)
print(json.dumps({"path": str(built["path"]), "targets": built["targets"]}))
"""

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from _package_adapter import METASALMONPY_REQUIREMENT, METASALMONPY_VERSION  # noqa: E402

LIVE = os.environ.get("SMN_PLUGIN_LIVE_ADAPTERS") == "1" and shutil.which("uv") is not None


def run_json(command: list[str], payload: dict) -> dict:
    proc = subprocess.run(
        command,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"{command} exited {proc.returncode}: {proc.stderr}")
    return json.loads(proc.stdout)


class OfflineAdapterTests(unittest.TestCase):
    @unittest.skipIf(
        importlib.util.find_spec("metasalmonpy") is not None,
        "metasalmonpy is importable here, so there is no missing-package path to test",
    )
    def test_plain_python_reports_missing_package_as_json(self) -> None:
        for script in ADAPTERS:
            with self.subTest(script=script.name):
                payload = run_json([sys.executable, str(script)], {"action": "runtime"})
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["error"]["code"], "missing_package")
                self.assertEqual(payload["pinned_requirement"], METASALMONPY_REQUIREMENT)


@unittest.skipUnless(LIVE, "set SMN_PLUGIN_LIVE_ADAPTERS=1 with uv on PATH to run the live adapter tests")
class LiveAdapterTests(unittest.TestCase):
    def adapter(self, script: Path, payload: dict) -> dict:
        return run_json(["uv", "run", "-q", str(script)], payload)

    def package_answer(self, expression: str):
        """Ask metasalmonpy directly, outside any adapter."""
        code = f"import json, metasalmonpy; print(json.dumps({expression}))"
        proc = subprocess.run(
            ["uv", "run", "-q", "--no-project", "--with", METASALMONPY_REQUIREMENT, "python", "-c", code],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_both_adapters_run_the_pinned_release(self) -> None:
        for script in ADAPTERS:
            with self.subTest(script=script.name):
                payload = self.adapter(script, {"action": "runtime"})
                self.assertTrue(payload["ok"], payload)
                self.assertEqual(payload["runtime"]["package_version"], METASALMONPY_VERSION)
                self.assertTrue(payload["runtime"]["matches_pin"])

    def test_sources_for_role_is_the_package_answer(self) -> None:
        for role in ("unit", "entity", "statistical_modifier", None):
            with self.subTest(role=role):
                payload = self.adapter(SALMON_TERMS, {"action": "sources_for_role", "role": role})
                self.assertTrue(payload["ok"], payload)
                expected = self.package_answer(f"metasalmonpy.sources_for_role({role!r})")
                self.assertEqual(payload["sources"], expected)

    def run_replay(self, mode: str) -> dict:
        proc = subprocess.run(
            ["uv", "run", "-q", str(REPLAY), mode], capture_output=True, text=True, timeout=900, check=False
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        return json.loads(proc.stdout)

    def test_review_actions_round_trip_a_packet_through_the_pinned_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sdp = Path(tmp) / "sdp"
            proc = subprocess.run(
                ["uv", "run", "-q", "--no-project", "--with", METASALMONPY_REQUIREMENT, "python", "-c", BUILD_PACKET, str(sdp)],
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            built = json.loads(proc.stdout)
            packet = json.loads(Path(built["path"]).read_text(encoding="utf-8"))
            judgements = [
                {"unit_key": unit["unit_key"], "dictionary_role": slot["dictionary_role"], "llm_decision": "review",
                 "llm_confidence": 0.5, "llm_rationale": "No candidate to weigh."}
                for unit in packet["units"]
                for slot in unit["slots"]
            ]
            written = self.adapter(METASALMON_API, {
                "action": "write_assessments", "packet": built["path"], "provider": "claude-code",
                "model": "live-test", "judgements": judgements,
            })
            self.assertTrue(written["ok"], written)
            self.assertEqual((written["rows"], written["unanswered"]), (built["targets"], []))
            ingested = self.adapter(METASALMON_API, {"action": "ingest_assessments", "path": str(sdp)})
            self.assertTrue(ingested["ok"], ingested)
            self.assertEqual(ingested["status"], "complete")
            self.assertEqual(ingested["summary"]["decisions"]["review"], built["targets"])
            self.assertTrue(Path(ingested["record_file"]).is_file())

    def test_the_theme_a_replay_controls_pass_on_the_pinned_release(self) -> None:
        report = self.run_replay("controls")
        self.assertEqual(len(report["reproduced"]), 9)
        self.assertEqual(report["oracles"], "pass")
        self.assertTrue(report["negative_control"])

    def test_the_recorded_cohort_still_passes_its_oracles(self) -> None:
        report = self.run_replay("cohort")
        self.assertEqual(report["status"], "pass", report)

    def test_metasalmon_skill_points_term_search_at_salmon_terms(self) -> None:
        payload = self.adapter(METASALMON_API, {"action": "find_terms", "query": "escapement"})
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "moved_action")
        self.assertIn("salmon-terms", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()
