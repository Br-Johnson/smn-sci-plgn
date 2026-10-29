"""Credential regressions at the source JSON/CLI and authenticated HTTP seams.

Fixtures contain invented credentials only. The CLI transport is a fake external
API; later HTTP checks use local servers and never contact real source services.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
from urllib.parse import parse_qsl, urlsplit
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "invented-fixture-token-7x9"
PASSWORD = "invented-fixture-password-4q2"
SOURCE_SCRIPTS = {
    "rmis": ROOT / "skills/rmis-skill/scripts/rmis_api.py",
    "ptagis": ROOT / "skills/ptagis-skill/scripts/ptagis_api.py",
    "streamnet": ROOT / "skills/streamnet-api-skill/scripts/streamnet_api.py",
}
sys.path.insert(0, str(ROOT / "scripts"))
from _common import http_get_json

AUTH_ENV = (
    "RMIS_API_KEY", "RMPC_API_KEY", "RMIS_JWT", "RMIS_EMAIL", "RMIS_PASSWORD",
    "PTAGIS_API_TOKEN", "PTAGIS_API_KEY", "STREAMNET_API_KEY",
)
# Patching urllib is the external API seam. The real script and all plugin
# plumbing run unchanged, including JSON parsing, output and file persistence.
CLI_DRIVER = r'''
import io, json, runpy, sys, urllib.error, urllib.request
class Response:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return sys.argv[2].encode()
    def geturl(self): return self.url
def open_fixture(*args, **kwargs):
    fixture = json.loads(sys.argv[2])
    if fixture.get("fixture_forbid_transport"):
        raise AssertionError("refused fixture reached external transport")
    if fixture.get("fixture_http_error"):
        raise urllib.error.HTTPError("https://fixture.invalid/response", 401, "Unauthorized", {}, io.BytesIO(json.dumps(fixture).encode()))
    response = Response()
    response.url = next(arg.full_url for arg in args if isinstance(arg, urllib.request.Request))
    return response
urllib.request.urlopen = open_fixture
urllib.request.OpenerDirector.open = open_fixture
runpy.run_path(sys.argv[1], run_name="__main__")
'''


def run_cli(source, payload, response=None, extra_env=None):
    environment = {key: value for key, value in os.environ.items() if key not in AUTH_ENV}
    environment.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-c", CLI_DRIVER, str(SOURCE_SCRIPTS[source]), json.dumps(response or {})],
        input=json.dumps(payload), text=True, capture_output=True, env=environment,
        timeout=15, check=False,
    )


class SourceCredentialCliTests(unittest.TestCase):
    def test_rmis_login_refuses_chat_credentials_without_returning_a_token(self):
        result = run_cli("rmis", {"action": "login", "email": "invented@example.invalid", "password": PASSWORD}, {"token": TOKEN})
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        self.assertNotIn(PASSWORD, result.stdout + result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response["error"]["code"], "local_auth_required")
        self.assertFalse(response["ok"])


    def test_source_requests_refuse_inline_credentials(self):
        for source, action, field in (("rmis", "release", "auth_token"), ("ptagis", "interrogation_site_codes", "auth_token"), ("streamnet", "tables", "api_key")):
            with self.subTest(source=source):
                result = run_cli(source, {"action": action, field: TOKEN})
                self.assertNotIn(TOKEN, result.stdout + result.stderr)
                response = json.loads(result.stdout)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "inline_credentials_refused")


    def test_environment_credentials_and_response_tokens_are_redacted_in_output_and_saved_data(self):
        cases = (("rmis", {"action": "release"}, "RMIS_API_KEY"), ("ptagis", {"action": "interrogation_site_codes"}, "PTAGIS_API_TOKEN"), ("streamnet", {"action": "table", "table_id": "fixture"}, "STREAMNET_API_KEY"))
        with tempfile.TemporaryDirectory() as directory:
            for source, payload, variable in cases:
                with self.subTest(source=source):
                    path = Path(directory) / f"{source}.json"
                    fixture = {"records": [{"label": "permitted metadata", "note": f"echo {TOKEN}", "access_token": PASSWORD}]}
                    result = run_cli(source, {**payload, "save_raw": True, "raw_output_path": str(path)}, fixture, {variable: TOKEN})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    response = json.loads(result.stdout)
                    self.assertTrue(response["ok"], response)
                    combined = result.stdout + result.stderr + path.read_text()
                    self.assertNotIn(TOKEN, combined)
                    self.assertNotIn(PASSWORD, combined)
                    self.assertIn("permitted metadata", combined)


    def test_authenticated_error_bodies_do_not_export_unknown_credentials(self):
        for source, action, variable in (("rmis", "release", "RMIS_API_KEY"), ("ptagis", "interrogation_site_codes", "PTAGIS_API_TOKEN"), ("streamnet", "tables", "STREAMNET_API_KEY")):
            with self.subTest(source=source):
                result = run_cli(source, {"action": action}, {"fixture_http_error": True, "echo": TOKEN, "access_token": PASSWORD}, {variable: TOKEN})
                self.assertNotIn(TOKEN, result.stdout + result.stderr)
                self.assertNotIn(PASSWORD, result.stdout + result.stderr)
                self.assertFalse(json.loads(result.stdout)["ok"])


    def test_invalid_request_does_not_put_environment_credentials_in_tracebacks(self):
        for source, action, variable in (("rmis", "release", "RMIS_API_KEY"), ("ptagis", "interrogation_site_codes", "PTAGIS_API_TOKEN"), ("streamnet", "tables", "STREAMNET_API_KEY")):
            with self.subTest(source=source):
                result = run_cli(source, {"action": action, "timeout_sec": TOKEN}, extra_env={variable: TOKEN})
                self.assertNotIn(TOKEN, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(json.loads(result.stdout)["ok"])


    def test_query_credentials_are_refused_without_echoing_the_value(self):
        for source, action in (("rmis", "release"), ("ptagis", "interrogation_site_codes"), ("streamnet", "tables")):
            with self.subTest(source=source):
                params = "api_key=" + TOKEN if source == "rmis" else {"api_key": TOKEN}
                result = run_cli(source, {"action": action, "params": params})
                self.assertNotIn(TOKEN, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["error"]["code"], "inline_credentials_refused")


    def test_rmis_raw_query_credentials_are_refused_when_the_value_contains_question_marks(self):
        inline = "invented-inline-fixture-token-629?continued?value"
        result = run_cli("rmis", {"action": "release", "params": "api_key=" + inline}, {"fixture_forbid_transport": True}, {"RMIS_API_KEY": TOKEN})
        self.assertNotIn(inline, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["error"]["code"], "inline_credentials_refused")


    def test_identifier_fields_cannot_introduce_credential_query_parameters(self):
        inline = "invented-inline-fixture-token-629"
        cases = (
            ("streamnet", {"action": "table", "table_id": "fixture"}, "table_id"),
            ("streamnet", {"action": "records", "record_id": "fixture"}, "record_id"),
            ("ptagis", {"action": "site_observations", "site_code": "TEST", "year": 2000}, "site_code"),
            ("ptagis", {"action": "site_observations", "site_code": "TEST", "year": 2000}, "year"),
            ("ptagis", {"action": "interrogation_files", "project_code": "TEST", "year": 2000}, "project_code"),
            ("ptagis", {"action": "interrogation_files", "site_code": "TEST", "year": 2000}, "site_code"),
            ("ptagis", {"action": "interrogation_files", "site_code": "TEST", "year": 2000}, "year"),
            ("ptagis", {"action": "validation_codes", "kind": "mrr_codes", "domain": "fixture"}, "domain"),
            ("ptagis", {"action": "reports", "user_name": "fixture"}, "user_name"),
            ("ptagis", {"action": "report_file", "user_name": "fixture", "report_name": "fixture"}, "report_name"),
        )
        for source, payload, field in cases:
            with self.subTest(source=source, action=payload["action"], field=field):
                result = run_cli(source, {**payload, field: "fixture?api_key=" + inline}, {"fixture_forbid_transport": True}, {"STREAMNET_API_KEY" if source == "streamnet" else "PTAGIS_API_TOKEN": TOKEN})
                self.assertNotIn(inline, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["error"]["code"], "inline_credentials_refused")


    def test_legitimate_raw_query_values_keep_their_question_marks(self):
        for params in ("search=cohort?age=1&perpage=1", "?search=cohort?age=1&perpage=1"):
            with self.subTest(params=params):
                result = run_cli("rmis", {"action": "release", "params": params}, extra_env={"RMIS_API_KEY": TOKEN})
                response = json.loads(result.stdout)
                self.assertTrue(response["ok"], response)
                self.assertEqual(parse_qsl(urlsplit(response["url"]).query), [("search", "cohort?age=1"), ("perpage", "1")])

    def test_identifiers_are_encoded_as_opaque_segments_without_changing_ordinary_ids(self):
        cases = (
            ("streamnet", {"action": "table", "table_id": "stock/one ?version#β"}, "https://api.streamnet.org/api/v1/ca/tables/stock%2Fone%20%3Fversion%23%CE%B2"),
            ("streamnet", {"action": "records", "record_id": 123}, "https://api.streamnet.org/api/v1/ca/123"),
            ("ptagis", {"action": "site_observations", "site_code": "TEST-1", "year": 2000}, "https://api.ptagis.org/data/interrogation/site/TEST-1/year/2000/observations"),
            ("ptagis", {"action": "interrogation_files", "project_code": "TEST_1", "year": 2000}, "https://api.ptagis.org/files/mrr/sites/TEST_1/year/2000"),
            ("ptagis", {"action": "report_file", "user_name": "analyst@example.invalid", "report_name": "Annual / effort?2026#draft β"}, "https://api.ptagis.org/reporting/reports/analyst%40example.invalid/file/Annual%20%2F%20effort%3F2026%23draft%20%CE%B2"),
        )
        for source, payload, expected_url in cases:
            with self.subTest(source=source, action=payload["action"]):
                result = run_cli(source, payload)
                response = json.loads(result.stdout)
                self.assertTrue(response["ok"], response)
                self.assertEqual(response["url"], expected_url)


class AuthenticatedHttpPolicyTests(unittest.TestCase):
    def test_credentials_need_an_explicit_destination_policy(self):
        class Response:
            status = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"label":"permitted metadata"}'
        with patch("urllib.request.urlopen", return_value=Response()):
            with self.assertRaises(RuntimeError) as refused:
                http_get_json("https://fixture.invalid/metadata", headers={"Authorization": TOKEN})
        self.assertNotIn(TOKEN, str(refused.exception))


    def test_authenticated_transport_exceptions_do_not_include_credential_values(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=urllib.error.URLError(TOKEN)):
            with self.assertRaises(RuntimeError) as refused:
                http_get_json("https://fixture.invalid/metadata", headers={"Authorization": TOKEN}, allowed_origins=("https://fixture.invalid",))
        self.assertNotIn(TOKEN, str(refused.exception))


    def test_final_url_credentials_are_refused_before_any_transport(self):
        class Response:
            status = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{}'
        inline = "invented-inline-fixture-token-629"
        urls = (
            "https://fixture.invalid/metadata?api_key=" + inline,
            "https://fixture.invalid/metadata?search=normal&api%5Fkey=" + inline,
            "https://fixture.invalid/metadata#access_token=" + inline,
            "https://fixture.invalid/metadata/fixture%3Fapi_key%3D" + inline,
        )
        for url in urls:
            for headers in ({}, {"Authorization": TOKEN}):
                with self.subTest(url=url, authenticated=bool(headers)):
                    with patch("urllib.request.urlopen", return_value=Response()) as anonymous, patch("urllib.request.OpenerDirector.open", return_value=Response()) as authenticated:
                        with self.assertRaises(RuntimeError) as refused:
                            http_get_json(url, headers=headers, allowed_origins=("https://fixture.invalid",))
                        self.assertNotIn(inline, str(refused.exception))
                        anonymous.assert_not_called()
                        authenticated.assert_not_called()


@unittest.skipUnless(shutil.which("openssl"), "local TLS fixtures require openssl")
class AuthenticatedHttpRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        cls.certificate = root / "certificate.pem"
        private_key = root / "fixture-key.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(private_key), "-out", str(cls.certificate), "-days", "1",
            "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ], capture_output=True, check=True, timeout=15)
        cls.received = []
        cls.redirects = {}
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                cls.received.append({"port": self.server.server_port, "path": self.path,
                    "authorization_received": self.headers.get("Authorization") == TOKEN,
                    "api_key_received": self.headers.get("XApiKey") == TOKEN})
                if self.path in cls.redirects:
                    self.send_response(302)
                    self.send_header("Location", cls.redirects[self.path])
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"label": "permitted metadata", "authenticated": self.headers.get("Authorization") == TOKEN}).encode())
            def log_message(self, *args): pass
        cls.servers = []
        for use_tls in (True, True, False):
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            if use_tls:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(cls.certificate, private_key)
                server.socket = context.wrap_socket(server.socket, server_side=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            cls.servers.append(server)
        cls.origin = f"https://localhost:{cls.servers[0].server_port}"
        cls.foreign_origin = f"https://127.0.0.1:{cls.servers[1].server_port}"
        cls.http_origin = f"http://127.0.0.1:{cls.servers[2].server_port}"
        cls.redirects.update({"/same-origin": "/metadata", "/cross-origin": cls.foreign_origin + "/metadata", "/downgrade": cls.http_origin + "/metadata"})

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        cls.directory.cleanup()

    def setUp(self):
        self.received.clear()
        self.trust = patch.dict(os.environ, {"SSL_CERT_FILE": str(self.certificate)})
        self.trust.start()
        self.addCleanup(self.trust.stop)

    def test_cross_origin_redirect_is_refused_before_the_destination_receives_credentials(self):
        with self.assertRaises(RuntimeError):
            http_get_json(self.origin + "/cross-origin", headers={"Authorization": TOKEN, "XApiKey": TOKEN}, allowed_origins=(self.origin,))
        self.assertFalse(any(event["port"] == self.servers[1].server_port for event in self.received))


    def test_same_origin_https_redirect_keeps_permitted_metadata_and_authentication(self):
        data, _ = http_get_json(self.origin + "/same-origin", headers={"Authorization": TOKEN, "XApiKey": TOKEN}, allowed_origins=(self.origin,))
        self.assertEqual(data, {"label": "permitted metadata", "authenticated": True})
        self.assertTrue(all(event["authorization_received"] and event["api_key_received"] for event in self.received))

    def test_https_downgrade_is_refused_before_the_http_destination_is_contacted(self):
        with self.assertRaises(RuntimeError):
            http_get_json(self.origin + "/downgrade", headers={"Authorization": TOKEN}, allowed_origins=(self.origin,))
        self.assertFalse(any(event["port"] == self.servers[2].server_port for event in self.received))

    def test_http_and_unapproved_initial_origins_are_refused_before_contact(self):
        for destination in (self.http_origin, self.foreign_origin):
            with self.subTest(destination=destination):
                with self.assertRaises(RuntimeError):
                    http_get_json(destination + "/metadata", headers={"Authorization": TOKEN}, allowed_origins=(self.origin,))
        self.assertEqual(self.received, [])

    def test_rmis_transport_uses_the_same_redirect_boundary(self):
        spec = importlib.util.spec_from_file_location("rmis_credential_transport", SOURCE_SCRIPTS["rmis"])
        rmis = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rmis)
        headers = {"Authorization": TOKEN}
        status, body, _, _ = rmis.fetch(self.origin + "/same-origin", headers=headers, allowed_origins=(self.origin,))
        self.assertEqual((status, json.loads(body)), (200, {"label": "permitted metadata", "authenticated": True}))
        for route in ("/cross-origin", "/downgrade"):
            with self.subTest(route=route):
                with self.assertRaises(RuntimeError):
                    rmis.fetch(self.origin + route, headers=headers, allowed_origins=(self.origin,))
        self.assertFalse(any(event["port"] in {self.servers[1].server_port, self.servers[2].server_port} for event in self.received))


    def test_same_origin_redirect_cannot_introduce_query_credentials(self):
        inline = "invented-inline-fixture-token-629"
        self.redirects["/credential-query"] = self.origin + "/metadata?api_key=" + inline
        self.addCleanup(self.redirects.pop, "/credential-query")
        with self.assertRaises(RuntimeError) as refused:
            http_get_json(self.origin + "/credential-query", headers={"Authorization": TOKEN}, allowed_origins=(self.origin,))
        self.assertNotIn(inline, str(refused.exception))
        self.assertFalse(any(event["path"].startswith("/metadata") for event in self.received))


if __name__ == "__main__":
    unittest.main()
