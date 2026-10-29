"""The JSON adapter against actual metasalmonpy v0.6.0, with network refused.

Set SMN_PLUGIN_PINNED_PYTHON to an existing pinned-release interpreter to run
without acquiring dependencies. The existing live-adapter CI profile instead
executes each command inside uv's pinned runtime; an interpreter path need not
survive uv's process. Neither route contacts ontology services: only the
transport boundaries are replaced in the child process.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "skills/salmon-terms/scripts/salmon_terms.py"
FIXTURES = ROOT / "tests/fixtures/ontology-releases"
REQUIREMENT = "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0"
COMMIT = "58aff2363519693345d4efdebe8a2027d948f6ce"
ENABLED = bool(os.environ.get("SMN_PLUGIN_PINNED_PYTHON")) or os.environ.get("SMN_PLUGIN_LIVE_ADAPTERS") == "1"
NO_NETWORK = """
import socket, urllib.request, requests
network_attempts = 0
def refused(*args, **kwargs):
    global network_attempts
    network_attempts += 1
    raise RuntimeError("LIVE_NETWORK_DISABLED: snapshot tests may not use a service")
socket.create_connection = refused
urllib.request.urlopen = refused
requests.sessions.Session.request = refused
"""


@unittest.skipUnless(ENABLED, "set SMN_PLUGIN_PINNED_PYTHON or enable the pinned live-adapter profile")
class SnapshotAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        python = os.environ.get("SMN_PLUGIN_PINNED_PYTHON")
        cls.python_command = [python] if python else [
            "uv", "run", "-q", "--no-project", "--with", REQUIREMENT, "python",
        ]
        provenance = cls.run_python("""
import importlib.metadata as metadata, json, metasalmonpy
print(json.dumps({"version": metasalmonpy.__version__,
    "origin": json.loads(metadata.distribution("metasalmonpy").read_text("direct_url.json"))}))
""", timeout=900)
        if provenance["version"] != "0.6.0" or provenance["origin"].get("vcs_info", {}).get("commit_id") != COMMIT:
            raise AssertionError("snapshot controls require the actual pinned v0.6.0 Git release")

    @classmethod
    def run_python(cls, code, *args, payload=None, env=None, timeout=60):
        child_env = dict(os.environ)
        child_env.pop("PYTHONPATH", None)
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        if env:
            child_env.update(env)
        result = subprocess.run(
            [*cls.python_command, "-c", NO_NETWORK + code + "\nassert network_attempts == 0, 'unexpected service request'\n",
             *map(str, args)],
            input=None if payload is None else json.dumps(payload),
            text=True, capture_output=True, timeout=timeout, env=child_env, check=False,
        )
        if result.returncode:
            raise AssertionError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    def adapter(self, payload):
        return self.run_python("import runpy, sys; runpy.run_path(sys.argv[1], run_name='__main__')",
                               ADAPTER, payload=payload)

    def direct(self, query, **kwargs):
        return self.run_python("""
import json, sys, metasalmonpy
frame = metasalmonpy.find_terms(sys.argv[1], **json.loads(sys.argv[2]))
print(json.dumps({"results": json.loads(frame.to_json(orient="records")),
    "ontology_release": (json.loads(frame.attrs["ontology_release"].to_json(orient="records"))
                         if "ontology_release" in frame.attrs else None)}))
""", query, json.dumps(kwargs))

    def test_uv_bootstrap_keeps_execution_inside_the_runtime_lifetime(self):
        result = self.run_python("""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
root = Path(sys.argv[1])
with tempfile.TemporaryDirectory() as temporary:
    folder = Path(temporary)
    shim = folder / "uv"
    shutil.copyfile(root / "tests/fixtures/expired_uv.py", shim)
    shim.chmod(0o755)
    log = folder / "uv.jsonl"
    env = dict(os.environ)
    env.pop("SMN_PLUGIN_PINNED_PYTHON", None)
    env.update(SMN_PLUGIN_LIVE_ADAPTERS="1", SMN_TEST_ACTIVE_PYTHON=sys.executable,
               SMN_TEST_UV_LOG=str(log), PATH=str(folder) + os.pathsep + env["PATH"])
    child = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover",
        "-s", str(root / "tests"), "-p", "test_term_snapshot_controls.py",
        "-k", "test_exact_smn_snapshot_keeps_the_package_results_and_provenance"],
        env=env, text=True, capture_output=True, timeout=30)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    print(json.dumps({"returncode": child.returncode, "stderr": child.stderr,
                      "calls": calls}))
""", ROOT)
        self.assertEqual(result["returncode"], 0, result["stderr"])
        self.assertGreaterEqual(len(result["calls"]), 3)
        self.assertTrue(all(call["mode"] == "execute" for call in result["calls"]))

    def test_exact_smn_snapshot_keeps_the_package_results_and_provenance(self):
        controls = {"sources": ["smn"], "expand_query": False,
                    "release": {"smn": "0.0.3"},
                    "snapshot_dir": {"smn": str(FIXTURES / "smn-0.0.3")}}
        response = self.adapter({"action": "find_terms", "query": "escapement", **controls})
        expected = self.direct("escapement", **controls)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["results"], expected["results"])
        self.assertEqual(response["ontology_release"], expected["ontology_release"])
        self.assertEqual(response["results"][0]["iri"], "https://w3id.org/smn/Escapement")
        self.assertTrue(response["ontology_release"][0]["manifest_verified"])
        self.assertEqual(response["ontology_release"][0]["version_iri"], "https://w3id.org/smn/0.0.3")

    def test_misspelled_snapshot_control_is_an_explicit_input_error(self):
        for field in ("snapshot_dirs", "snapshot_dr", "releases", "relase"):
            with self.subTest(field=field):
                response = self.adapter({"action": "find_terms", "query": "escapement", "sources": [],
                                         field: {"smn": str(FIXTURES / "smn-0.0.3")}})
                self.assertFalse(response["ok"], response)
                self.assertEqual(response["error"]["code"], "invalid_input")
                self.assertIn(field, response["error"]["message"])

    def test_unsupported_source_is_refused_instead_of_successfully_finding_nothing(self):
        for sources in ([" PSC "], "psc", ["smn", "typo"]):
            with self.subTest(sources=sources):
                response = self.adapter({"query": "escapement", "sources": sources})
                self.assertFalse(response["ok"], response)
                self.assertEqual(response["error"]["code"], "unsupported_source")

    def test_exact_gcdfo_snapshot_keeps_the_package_results_and_provenance(self):
        controls = {"sources": ["gcdfo"], "expand_query": False,
                    "release": {"gcdfo": "0.0.9"},
                    "snapshot_dir": {"gcdfo": str(FIXTURES / "gcdfo-0.0.9")}}
        response = self.adapter({"query": "conservation unit", **controls})
        expected = self.direct("conservation unit", **controls)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["results"], expected["results"])
        self.assertEqual(response["ontology_release"], expected["ontology_release"])
        self.assertEqual(response["results"][0]["iri"], "https://w3id.org/gcdfo/salmon#ConservationUnit")
        self.assertEqual(response["ontology_release"][0]["version_iri"], "https://w3id.org/gcdfo/salmon/0.0.9")

    def test_a_snapshot_without_a_manifest_is_honestly_unverified(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "unverified"
            shutil.copytree(FIXTURES / "smn-0.0.3", snapshot)
            (snapshot / "MANIFEST.sha256").unlink()
            controls = {"sources": ["smn"], "expand_query": False, "snapshot_dir": {"smn": str(snapshot)}}
            response = self.adapter({"query": "escapement", **controls})
            expected = self.direct("escapement", **controls)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["ontology_release"], expected["ontology_release"])
        self.assertFalse(response["ontology_release"][0]["manifest_verified"])
        self.assertEqual(response["ontology_release"][0]["sha256"],
                         "465b54743a7283dac960ff70c33a71dcb3c505ecd66363690638e4ae56e02ac1")

    def test_a_missing_selected_snapshot_refuses_without_latest_fallback(self):
        response = self.adapter({"query": "escapement", "sources": ["smn"],
                                 "release": {"smn": "0.0.3"},
                                 "snapshot_dir": {"smn": str(FIXTURES / "missing")}})
        self.assertFalse(response["ok"], response)
        self.assertEqual(response["error"]["code"], "package_error")
        self.assertNotIn("LIVE_NETWORK_DISABLED", response["error"]["message"])
        self.assertIn("snapshot", response["error"]["message"].lower())

    def test_a_mismatched_release_refuses_without_latest_fallback(self):
        response = self.adapter({"query": "escapement", "sources": ["smn"],
                                 "release": {"smn": "0.0.4"},
                                 "snapshot_dir": {"smn": str(FIXTURES / "smn-0.0.3")}})
        self.assertFalse(response["ok"], response)
        self.assertIn("0.0.4", response["error"]["message"])
        self.assertNotIn("LIVE_NETWORK_DISABLED", response["error"]["message"])

    def test_a_checksum_mismatch_refuses_without_latest_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "changed"
            shutil.copytree(FIXTURES / "smn-0.0.3", snapshot)
            with (snapshot / "smn.owl").open("a") as handle:
                handle.write("\n")
            response = self.adapter({"query": "escapement", "sources": ["smn"],
                                     "snapshot_dir": {"smn": str(snapshot)}})
        self.assertFalse(response["ok"], response)
        self.assertIn("manifest", response["error"]["message"].lower())
        self.assertNotIn("LIVE_NETWORK_DISABLED", response["error"]["message"])

    def test_the_package_refuses_unsupported_or_malformed_release_controls(self):
        for controls in ({"release": {"psc": "0.0.3"}}, {"snapshot_dir": {"psc": "unused"}},
                         {"release": "0.0.3"}, {"snapshot_dir": ["unused"]}):
            with self.subTest(controls=controls):
                response = self.adapter({"query": "escapement", "sources": ["smn"], **controls})
                self.assertFalse(response["ok"], response)
                self.assertEqual(response["error"]["code"], "package_error")
                self.assertNotIn("LIVE_NETWORK_DISABLED", response["error"]["message"])

    def test_supported_source_normalization_remains_the_package_answer(self):
        controls = {"sources": [" SMN ", None, "smn", ""], "expand_query": False,
                    "snapshot_dir": {"smn": str(FIXTURES / "smn-0.0.3")}}
        response = self.adapter({"query": "escapement", **controls})
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["results"], self.direct("escapement", **controls)["results"])

    def test_malformed_source_shapes_are_explicit_input_errors(self):
        for sources in ({"smn": True}, [4], True):
            with self.subTest(sources=sources):
                response = self.adapter({"query": "escapement", "sources": sources})
                self.assertFalse(response["ok"], response)
                self.assertEqual(response["error"]["code"], "invalid_input")

    def test_an_unpinned_empty_search_does_not_claim_snapshot_provenance(self):
        response = self.adapter({"query": "escapement", "sources": []})
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["results"], [])
        self.assertIsNone(response["ontology_release"])

    def test_cache_enabled_same_bytes_keep_each_calls_manifest_state_and_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            verified = Path(temporary) / "verified"
            unverified = Path(temporary) / "unverified"
            for snapshot in (verified, unverified):
                shutil.copytree(FIXTURES / "smn-0.0.3", snapshot)
            (unverified / "MANIFEST.sha256").unlink()
            payloads = [{"query": "escapement", "sources": ["smn"], "expand_query": False,
                         "snapshot_dir": {"smn": str(snapshot)}} for snapshot in (verified, unverified)]
            responses = self.run_python("""
import contextlib, io, json, runpy, sys
application = runpy.run_path(sys.argv[1])
answers = []
for payload in json.loads(sys.argv[2]):
    sys.stdin = io.StringIO(json.dumps(payload))
    with contextlib.redirect_stdout(io.StringIO()) as output:
        application["main"]()
    answers.append(json.loads(output.getvalue()))
print(json.dumps(answers))
""", ADAPTER, json.dumps(payloads), env={"METASALMONPY_CACHE": "1"})
            for response, snapshot in zip(responses, (verified, unverified)):
                expected = self.direct("escapement", sources=["smn"], expand_query=False,
                                       snapshot_dir={"smn": str(snapshot)})
                self.assertTrue(response["ok"], response)
                self.assertEqual(response["ontology_release"], expected["ontology_release"])
        self.assertEqual(responses[0]["results"], responses[1]["results"])
        self.assertEqual([response["ontology_release"][0]["manifest_verified"] for response in responses],
                         [True, False])
