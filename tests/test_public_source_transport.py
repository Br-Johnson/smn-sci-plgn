"""Public source CLI/HTTP regressions with fake APIs and local TLS fixtures only."""
from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {
    "critfc": ROOT / "skills/critfc-crosswalk-skill/scripts/critfc_crosswalk.py",
    "noaa": ROOT / "skills/noaa-sps-skill/scripts/noaa_sps.py",
    "npafc": ROOT / "skills/npafc-skill/scripts/npafc_catalog.py",
    "dart": ROOT / "skills/dart-query-skill/scripts/dart_query_catalog.py",
    "pubmed": ROOT / "skills/salmon-literature-skill/scripts/salmon_literature.py",
    "ptagis": ROOT / "skills/ptagis-skill/scripts/ptagis_api.py",
    "streamnet": ROOT / "skills/streamnet-api-skill/scripts/streamnet_api.py",
    "rmis": ROOT / "skills/rmis-skill/scripts/rmis_api.py",
}
sys.path.insert(0, str(ROOT / "scripts"))
from _common import http_get_json

AUTH_NAMES = ("RMIS_API_KEY", "RMPC_API_KEY", "RMIS_JWT", "RMIS_EMAIL", "RMIS_PASSWORD", "PTAGIS_API_TOKEN", "PTAGIS_API_KEY", "STREAMNET_API_KEY")
DRIVER = r'''
import io, json, runpy, socket, ssl, sys, urllib.error, urllib.request
fixture = json.loads(sys.argv[2])
class Response:
    status = 200
    def __init__(self, url):
        self.url = url
        self.headers = {"Content-Type": fixture.get("content_type", "text/html")}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def geturl(self): return fixture.get("final_url", self.url)
    def read(self, *args): return fixture.get("body", "<html><title>Fixture metadata</title></html>").encode()
def fake_open(*args, **kwargs):
    req = next(arg for arg in args if isinstance(arg, urllib.request.Request))
    if fixture.get("failure") == "timeout":
        raise TimeoutError("invented diagnostic must not be emitted")
    if fixture.get("failure") == "tls":
        raise urllib.error.URLError(ssl.SSLCertVerificationError("invented diagnostic must not be emitted"))
    if fixture.get("failure") == "dns":
        raise urllib.error.URLError(socket.gaierror(-2, "invented diagnostic must not be emitted"))
    if fixture.get("status", 200) >= 400:
        raise urllib.error.HTTPError(fixture.get("final_url", req.full_url), fixture["status"], "invented diagnostic must not be emitted", {"Retry-After": "60"}, io.BytesIO(b"invented diagnostic must not be emitted" * 1000))
    if fixture.get("forbid_transport"):
        raise AssertionError("request reached forbidden external fixture")
    return Response(req.full_url)
urllib.request.urlopen = fake_open
urllib.request.OpenerDirector.open = fake_open
runpy.run_path(sys.argv[1], run_name="__main__")
'''


def run_cli(source, payload, fixture=None):
    environment = {key: value for key, value in os.environ.items() if key not in AUTH_NAMES}
    return subprocess.run([sys.executable, "-c", DRIVER, str(SCRIPTS[source]), json.dumps(fixture or {})],
        input=json.dumps(payload), capture_output=True, text=True, env=environment, timeout=20, check=False)


class PublicSourceCliTests(unittest.TestCase):
    def test_named_sources_refuse_unrelated_hosts_before_transport(self):
        for source in ("critfc", "noaa", "npafc", "dart"):
            with self.subTest(source=source):
                payload = {"action": "page", "path": "https://unrelated.example.invalid/metadata"} if source == "dart" else {"action": "request", "url": "https://unrelated.example.invalid/metadata"}
                result = run_cli(source, payload)
                self.assertEqual(result.returncode, 0, result.stderr)
                response = json.loads(result.stdout)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "destination_refused")


    def test_dns_failures_return_bounded_typed_json_across_source_adapters(self):
        payloads = {"critfc": {"action": "page"}, "noaa": {"action": "home"}, "npafc": {"action": "dataset_search"}, "dart": {"action": "page", "name": "adult_passage_counts"}, "pubmed": {"query": "synthetic"}, "ptagis": {"action": "validation_codes", "kind": "revision_date"}, "streamnet": {"action": "tables"}, "rmis": {"action": "announcement"}}
        for source, payload in payloads.items():
            with self.subTest(source=source):
                result = run_cli(source, payload, {"failure": "dns"})
                self.assertEqual(result.returncode, 0)
                response = json.loads(result.stdout)
                self.assertEqual((response["ok"], response["error"]["code"], response["outcome"]), (False, "dns_error", "unavailable"))
                self.assertNotIn("invented diagnostic", result.stdout + result.stderr)
                self.assertLess(len(result.stdout.encode()), 4096)


    def test_timeout_and_tls_failures_are_distinct_without_diagnostic_leaks(self):
        payloads = {"critfc": {"action": "page"}, "noaa": {"action": "home"}, "npafc": {"action": "dataset_search"}, "dart": {"action": "page", "name": "adult_passage_counts"}, "pubmed": {"query": "synthetic"}, "ptagis": {"action": "validation_codes", "kind": "revision_date"}, "streamnet": {"action": "tables"}, "rmis": {"action": "announcement"}}
        for source, payload in payloads.items():
            for failure, code in (("timeout", "timeout"), ("tls", "tls_error")):
                with self.subTest(source=source, failure=failure):
                    result = run_cli(source, payload, {"failure": failure})
                    self.assertEqual(result.returncode, 0)
                    response = json.loads(result.stdout)
                    self.assertEqual((response["error"]["code"], response["outcome"]), (code, "unavailable"))
                    self.assertNotIn("invented diagnostic", result.stdout + result.stderr)
                    self.assertLess(len(result.stdout.encode()), 4096)


    def test_http_unauthorized_rate_limit_and_unavailability_remain_distinct(self):
        payloads = {"critfc": {"action": "page"}, "noaa": {"action": "home"}, "npafc": {"action": "dataset_search"}, "dart": {"action": "page", "name": "adult_passage_counts"}, "pubmed": {"query": "synthetic"}, "ptagis": {"action": "validation_codes", "kind": "revision_date"}, "streamnet": {"action": "tables"}, "rmis": {"action": "announcement"}}
        for source, payload in payloads.items():
            for status, code, outcome in ((401, "unauthorized", "unauthorized"), (429, "rate_limited", "rate_limited"), (503, "http_unavailable", "unavailable")):
                with self.subTest(source=source, status=status):
                    result = run_cli(source, payload, {"status": status})
                    self.assertEqual(result.returncode, 0)
                    response = json.loads(result.stdout)
                    self.assertEqual((response["ok"], response["error"]["code"], response["outcome"], response["status"]), (False, code, outcome, status))
                    self.assertNotIn("invented diagnostic", result.stdout + result.stderr)
                    self.assertLess(len(result.stdout.encode()), 4096)


    def test_http_redirect_failure_retains_validated_final_origin(self):
        for status, code in ((404, "not_found"), (429, "rate_limited")):
            with self.subTest(status=status):
                result = run_cli("noaa", {"action": "home"}, {
                    "status": status, "final_url": "https://webapps.nwfsc.noaa.gov/final?note=fictional"})
                response = json.loads(result.stdout)
                self.assertEqual(response["error"]["code"], code)
                self.assertEqual(response["retrieval"][0]["requested_url"], "https://www.webapps.nwfsc.noaa.gov")
                self.assertEqual(response["retrieval"][0]["final_origin"], "https://webapps.nwfsc.noaa.gov")
                self.assertNotIn("fictional", result.stdout)
        refused = run_cli("noaa", {"action": "home"}, {
            "status": 404, "final_url": "https://unrelated.example.invalid/final"})
        self.assertEqual(json.loads(refused.stdout)["error"]["code"], "destination_refused")

    def test_malformed_json_is_a_typed_failure_in_every_json_consumer(self):
        payloads = {"critfc": {"action": "rest_root"}, "noaa": {"action": "request", "path": "/sps"}, "npafc": {"action": "dataset_search"}, "pubmed": {"query": "synthetic"}, "ptagis": {"action": "validation_codes", "kind": "revision_date"}, "streamnet": {"action": "tables"}, "rmis": {"action": "release"}}
        for source, payload in payloads.items():
            with self.subTest(source=source):
                result = run_cli(source, payload, {"content_type": "application/json", "body": "{invented diagnostic must not be emitted"})
                self.assertEqual(result.returncode, 0)
                response = json.loads(result.stdout)
                self.assertEqual((response["ok"], response["error"]["code"], response["outcome"]), (False, "malformed_json", "invalid_response"))
                self.assertNotIn("invented diagnostic", result.stdout + result.stderr)


    def test_success_records_the_actual_final_source_origin_and_retrieval_time(self):
        final = "https://www.critfc.org/metadata?edition=one"
        result = run_cli("critfc", {"action": "request", "url": "https://critfc.org/metadata"}, {"final_url": final})
        response = json.loads(result.stdout)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["url"], final)
        record = response["retrieval"][-1]
        self.assertEqual((record["requested_url"], record["final_url"], record["final_origin"], record["status"]), ("https://critfc.org/metadata", final, "https://www.critfc.org", 200))
        self.assertRegex(record["retrieved_at"], r"^\d{4}-\d{2}-\d{2}T.*Z$")


    def test_unapproved_final_origin_is_refused_before_content_is_attributed(self):
        for final in ("https://unrelated.example.invalid/metadata", "https://127.0.0.1/metadata", "https://critfc.org:444/metadata"):
            with self.subTest(final=final):
                result = run_cli("critfc", {"action": "request", "url": "https://critfc.org/metadata"}, {"final_url": final})
                response = json.loads(result.stdout)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "destination_refused")
                self.assertNotIn("records", response)


    def test_html_login_and_error_pages_are_not_successful_source_results(self):
        payloads = {"critfc": {"action": "page"}, "noaa": {"action": "home"}, "npafc": {"action": "dataset_search"}, "dart": {"action": "page", "name": "adult_passage_counts"}, "pubmed": {"query": "synthetic"}, "ptagis": {"action": "validation_codes", "kind": "revision_date"}, "streamnet": {"action": "tables"}, "rmis": {"action": "announcement"}}
        pages = (("<html><title>Sign in</title><input type='password'></html>", "html_login", "unauthorized"), ("<html><title>Service unavailable</title></html>", "html_error", "unavailable"))
        for source, payload in payloads.items():
            for body, code, outcome in pages:
                with self.subTest(source=source, code=code):
                    result = run_cli(source, payload, {"content_type": "text/html", "body": body})
                    response = json.loads(result.stdout)
                    self.assertEqual((response["ok"], response["error"]["code"], response["outcome"]), (False, code, outcome))
                    self.assertNotIn("<html>", result.stdout + result.stderr)


    def test_successful_empty_results_are_not_unavailable_results(self):
        cases = (("ptagis", {"action": "validation_codes", "kind": "revision_date"}, "[]"), ("streamnet", {"action": "tables"}, "[]"), ("rmis", {"action": "release"}, "[]"), ("pubmed", {"query": "synthetic"}, '{"esearchresult":{"idlist":[]}}'), ("npafc", {"action": "dataset_search"}, '{"success":true,"result":{"count":0,"results":[]}}'))
        for source, payload, body in cases:
            with self.subTest(source=source):
                result = run_cli(source, payload, {"content_type": "application/json", "body": body})
                response = json.loads(result.stdout)
                self.assertEqual((response["ok"], response["outcome"]), (True, "success_empty"))
                self.assertNotIn("error", response)


    def test_existing_source_queries_survive_additional_parameters(self):
        cases = (("noaa", "https://www.webapps.nwfsc.noaa.gov/apex/f?p=261:1::::::", [("p", "261:1::::::"), ("request", "view?one")]), ("rmis", "/release?page=1#view", [("page", "1"), ("request", "view?one")]))
        for source, target, expected in cases:
            with self.subTest(source=source):
                payload = {"action": "request", "url" if source == "noaa" else "path": target, "params": {"request": "view?one"}}
                result = run_cli(source, payload, {"content_type": "application/json", "body": "[]"})
                response = json.loads(result.stdout)
                self.assertTrue(response["ok"], response)
                self.assertEqual(parse_qsl(urlsplit(response["url"]).query), expected)


    def test_expected_public_host_variants_remain_available(self):
        variants = {"critfc": ("https://critfc.org", "https://www.critfc.org", "https://gis.critfc.org"), "noaa": ("https://www.webapps.nwfsc.noaa.gov", "https://webapps.nwfsc.noaa.gov", "https://www.fisheries.noaa.gov"), "npafc": ("https://npafc.org", "https://www.npafc.org", "https://data.npafc.org"), "dart": ("https://cbr.washington.edu", "https://www.cbr.washington.edu")}
        for source, origins in variants.items():
            for origin in origins:
                with self.subTest(source=source, origin=origin):
                    payload = {"action": "page", "path": origin + "/metadata"} if source == "dart" else {"action": "request", "url": origin + "/metadata"}
                    response = json.loads(run_cli(source, payload).stdout)
                    self.assertTrue(response["ok"], response)
                    self.assertEqual(response["retrieval"][-1]["final_origin"], origin)

    def test_public_actions_refuse_private_local_ports_and_non_https_schemes(self):
        for source in ("critfc", "noaa", "npafc", "dart"):
            for url in ("https://127.0.0.1/", "https://localhost/", "https://169.254.169.254/", "https://critfc.org:444/", "https://critfc.org:0/", "http://critfc.org/", "file:///invented/local/path"):
                with self.subTest(source=source, url=url):
                    payload = {"action": "page", "path": url} if source == "dart" else {"action": "request", "url": url}
                    response = json.loads(run_cli(source, payload, {"forbid_transport": True}).stdout)
                    self.assertFalse(response["ok"])
                    self.assertIn(response["error"]["code"], {"destination_refused", "https_required"})


@unittest.skipUnless(shutil.which("openssl"), "local TLS fixtures require openssl")
class PublicRedirectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        certificate = Path(cls.directory.name) / "certificate.pem"
        key = Path(cls.directory.name) / "fixture-key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(certificate), "-days", "1", "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"], capture_output=True, check=True, timeout=15)
        cls.certificate = certificate
        cls.received = []
        cls.redirects = {}
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                cls.received.append((self.server.server_port, self.path))
                if self.path in cls.redirects:
                    self.send_response(302)
                    self.send_header("Location", cls.redirects[self.path])
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"label":"fixture metadata"}')
            def log_message(self, *args): pass
        cls.servers = []
        for use_tls in (True, True, False):
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            if use_tls:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(certificate, key)
                server.socket = context.wrap_socket(server.socket, server_side=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            cls.servers.append(server)
        cls.origin = f"https://localhost:{cls.servers[0].server_port}"
        cls.variant = f"https://127.0.0.1:{cls.servers[1].server_port}"
        cls.insecure = f"http://127.0.0.1:{cls.servers[2].server_port}"
        cls.redirects.update({"/variant": cls.variant + "/metadata", "/downgrade": cls.insecure + "/metadata", "/same": "/metadata"})

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        cls.directory.cleanup()

    def setUp(self):
        self.received.clear()
        trust = patch.dict(os.environ, {"SSL_CERT_FILE": str(self.certificate)})
        trust.start()
        self.addCleanup(trust.stop)

    def test_unapproved_public_redirect_is_blocked_before_destination_contact(self):
        for route in ("/variant", "/downgrade"):
            with self.subTest(route=route):
                self.received.clear()
                with self.assertRaises(RuntimeError):
                    http_get_json(self.origin + route, allowed_origins=(self.origin,))
                self.assertFalse(any(port != self.servers[0].server_port for port, _ in self.received))


    def test_approved_public_redirects_preserve_metadata_and_real_final_url(self):
        for route, final in (("/same", self.origin + "/metadata"), ("/variant", self.variant + "/metadata")):
            with self.subTest(route=route):
                data, url = http_get_json(self.origin + route, allowed_origins=(self.origin, self.variant))
                self.assertEqual((data, url), ({"label": "fixture metadata"}, final))


if __name__ == "__main__":
    unittest.main()
