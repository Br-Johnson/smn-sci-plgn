"""Smoke tests for the two package adapters.

The offline test runs everywhere. It proves an adapter started with plain
``python3``, where metasalmonpy is not installed, answers with a JSON error
rather than a traceback, which also proves it imports nothing heavy at startup.

The live tests install metasalmonpy from its pinned tag through uv and call
it, so they need uv and network access. They run only when
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
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SALMON_TERMS = REPO_ROOT / "skills" / "salmon-terms" / "scripts" / "salmon_terms.py"
METASALMON_API = REPO_ROOT / "skills" / "metasalmon-skill" / "scripts" / "metasalmon_api.py"
ADAPTERS = (SALMON_TERMS, METASALMON_API)

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

    def test_metasalmon_skill_points_term_search_at_salmon_terms(self) -> None:
        payload = self.adapter(METASALMON_API, {"action": "find_terms", "query": "escapement"})
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "moved_action")
        self.assertIn("salmon-terms", payload["error"]["message"])


if __name__ == "__main__":
    unittest.main()
