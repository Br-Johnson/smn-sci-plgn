# Source transport contract

The eight network source adapters use `scripts/_common.py` for HTTP reads and
`scripts/_source_auth.py` for destination and credential policy. Every source
supplies explicit HTTPS origins. Requests and every redirect stay within that
source's allowed hosts and ports. Authenticated redirects retain the stricter
original-origin rule documented in [source authentication](source-authentication.md).

| Source | Allowed HTTPS hosts (port 443) |
| --- | --- |
| CRITFC | `critfc.org`, `www.critfc.org`, `gis.critfc.org` |
| NOAA SPS | `www.webapps.nwfsc.noaa.gov`, `webapps.nwfsc.noaa.gov`, `www.fisheries.noaa.gov` |
| NPAFC | `data.npafc.org`, `www.npafc.org`, `npafc.org` |
| DART | `www.cbr.washington.edu`, `cbr.washington.edu` |
| PubMed E-utilities | `eutils.ncbi.nlm.nih.gov` |
| PTAGIS | `api.ptagis.org` |
| StreamNet | `api.streamnet.org` |
| RMIS data / announcement | `phish.rmis.org` / `www.rmis.org`, `rmis.org` |

An origin being allowed is a policy choice, not an availability check. No live
source access is needed to run the synthetic regression suite. Local, private,
unrelated and alternate-port URLs supplied to named-source actions are refused.
The helpers accept an explicit local origin only in transport test fixtures;
source CLI inputs cannot replace an adapter's origin policy.

Results carry `retrieval` entries with the requested URL, real final URL and
origin, UTC retrieval time, HTTP status, content type and outcome. URL strings
are capped at 2048 characters with explicit truncation flags. Failure context
uses origins only, withholding query values, response bodies, arbitrary headers
and exception text. A source's content is assessed after successful retrieval.

| Outcome | Representative error codes |
| --- | --- |
| `refused` | `destination_refused`, `https_required`, credential-policy refusals |
| `unavailable` | `dns_error`, `timeout`, `tls_error`, `connection_error`, `not_found`, `http_unavailable`, `html_error` |
| `unauthorized` | `unauthorized` (401), `forbidden` (403), `html_login` |
| `rate_limited` | `rate_limited` (429) |
| `invalid_response` | `malformed_json`, `unexpected_html`, `invalid_encoding`, `source_api_error` |
| `success_empty` | A successful empty JSON result or source-declared empty search |
| `success` | A successful nonempty response |

JSON consumers refuse malformed JSON and unexpected HTML. Page adapters detect
common login/error titles and password forms; this is a conservative access-page
check, not a general assessment of page meaning. HTTP errors retain status but
never echo upstream body text. Unknown failures still return a safe JSON error.

Existing query strings and fragments remain intact when parameters are added.
Relative paths retain their source's documented default host; explicit URLs
require HTTPS and a permitted origin. Generic GET actions keep these same rules.

Verify the public CLI/HTTP seams with:

```sh
python3 -m unittest discover -s tests -p 'test_public_source_transport.py' -v
python3 -m unittest discover -s tests -p 'test_source_credentials.py' -v
```

These tests use injected external responses, invented diagnostic values and
local TLS servers. OpenSSL generates temporary fixture certificates; TLS tests
report skips when it is unavailable. They perform no live source query or login.

## Source error documents

A successful HTTP status is not sufficient for a successful source result. The
PubMed adapter requires the ESearch identifier-list and requested ESummary
records; top-level or per-record NCBI errors return bounded typed refusals. A
missing result envelope remains an invalid response, never a successful empty
search. See [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/).

The CRITFC ArcGIS reader recognizes top-level JSON error documents. Source codes
401/403/498/499 remain authorization failures, 429 remains rate-limited, and
other source errors remain unavailable. Upstream error text is withheld. See
[Esri token-required guidance](https://support.esri.com/en-us/knowledge-base/error-authentication-token-required-status-code-499-000022899).
The retrieval ledger retains the actual HTTP status (including 200), while the
typed outcome records the source refusal. No credentials are requested or
forwarded as a fallback. These controls use fictional responses, not live data.
