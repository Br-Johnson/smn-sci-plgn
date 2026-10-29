from __future__ import annotations

import contextvars
import datetime as dt
import json
import os
import re
import socket
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from _source_auth import SourcePolicyError, authenticated_headers, contains_inline_credentials, redact_credentials, source_urlopen, validate_source_destination


DEFAULT_TIMEOUT = 20
_RETRIEVALS = contextvars.ContextVar("source_retrievals", default=None)
_SOURCE = contextvars.ContextVar("source_context", default=None)


class SourceRequestError(RuntimeError):
    """A bounded public failure; never carries an upstream body or exception text."""
    def __init__(self, code: str, message: str, *, outcome: str = "unavailable", status: int | None = None):
        super().__init__(message)
        self.code, self.outcome, self.status = code, outcome, status
        records = _RETRIEVALS.get()
        if records:
            records[-1]["outcome"] = outcome
            self.status = status if status is not None else records[-1]["status"]
            record = records[-1]
            for key in ("requested_url", "final_url"):
                parsed = parse.urlsplit(record[key])
                record[key] = parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
            record["url_context"] = "origin_only"

    def as_result(self) -> dict[str, Any]:
        return {"ok": False, "outcome": self.outcome, "status": self.status,
                "error": {"code": self.code, "message": str(self)},
                **(_SOURCE.get() or {}), "retrieval": source_retrievals()}


def source_retrievals() -> list[dict[str, Any]]:
    return [dict(record) for record in (_RETRIEVALS.get() or [])]


def source_outcome() -> str:
    records = _RETRIEVALS.get() or []
    return "success_empty" if records and records[-1]["outcome"] == "success_empty" else "success"


def mark_source_empty(empty: bool) -> None:
    records = _RETRIEVALS.get()
    if empty and records:
        records[-1]["outcome"] = "success_empty"


def _record_retrieval(requested: str, final: str, status: int | None, content_type: str = "", *, outcome: str = "success") -> None:
    records = _RETRIEVALS.get()
    if records is None:
        return
    parsed = parse.urlsplit(final)
    origin = parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    records.append({"requested_url": requested[:2048], "final_url": final[:2048], "final_origin": origin,
        "requested_url_truncated": len(requested) > 2048, "final_url_truncated": len(final) > 2048,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status, "content_type": content_type[:128], "outcome": outcome})


def _record_unavailable(requested: str, final: str, status: int | None) -> None:
    # Failed requests expose origins only, never query values, bodies or reasons.
    def origin(url):
        parsed = parse.urlsplit(url)
        return parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    _record_retrieval(origin(requested), origin(final), status, outcome="unavailable")


def load_input() -> Any:
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("expected JSON on stdin")
    payload = json.loads(raw)
    context = _SOURCE.get()
    if context is not None and isinstance(payload, dict) and isinstance(payload.get("action"), str):
        context["action"] = payload["action"][:64]
    return payload


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(redact_credentials(payload), indent=2, sort_keys=True))
    sys.stdout.write("\n")


def result_error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": {"code": code, "message": message},
    }
    payload.update(extra)
    return payload


def inline_credentials_refused(payload: dict[str, Any]) -> bool:
    """Agent-facing JSON accepts credential references through the environment only."""
    if contains_inline_credentials(payload):
        emit(result_error(
            "inline_credentials_refused",
            "Do not send credentials through chat or JSON input. Configure the source credential in your own terminal environment.",
        ))
        return True
    return False


def build_url(base_url: str, params: dict[str, Any] | str | None = None) -> str:
    if not params:
        return base_url
    if isinstance(params, str):
        query = params.lstrip("?")
    elif isinstance(params, dict):
        query = parse.urlencode([(key, value) for key, value in params.items() if value is not None], doseq=True)
    else:
        raise ValueError("params must be an object, query string, or null")
    parsed = parse.urlsplit(base_url)
    combined = "&".join(part for part in (parsed.query, query) if part)
    return parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, combined, parsed.fragment))


def resolve_source_url(value: str, default_origin: str) -> str:
    if not isinstance(value, str):
        raise SourcePolicyError("invalid_source_url", "Source URLs and paths must be text.")
    parsed = parse.urlsplit(value)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != "https":
            raise SourcePolicyError("https_required", "Public source URLs require HTTPS.")
        return value
    return f"{default_origin}/{value.lstrip('/')}"


def http_get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_origins: tuple[str, ...] | None = None,
) -> tuple[bytes, dict[str, str], int, str]:
    full_url = build_url(url, params)
    req = request.Request(full_url, headers=headers or {}, method="GET")
    final_url, status = full_url, None
    try:
        with source_urlopen(req, timeout=timeout, allowed_origins=allowed_origins) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else full_url
            validate_source_destination(final_url, allowed_origins, authenticated_origin=full_url if authenticated_headers(headers) else None)
            status = response.status
            response_headers = {str(key).title(): value for key, value in response.headers.items()}
            body = response.read()
            _record_retrieval(full_url, final_url, status, response_headers.get("Content-Type", ""), outcome="success_empty" if not body else "success")
            _check_html_access_page(body, response_headers.get("Content-Type", ""))
            return body, response_headers, status, final_url
    except error.HTTPError as exc:
        _record_unavailable(full_url, final_url, exc.code)
        # Never echo HTTP bodies, reason strings or arbitrary headers, even for
        # public endpoints: an upstream login/error page can contain secrets.
        code, outcome, message = {
            401: ("unauthorized", "unauthorized", "The source requires authorization."),
            403: ("forbidden", "unauthorized", "The source refused access."),
            404: ("not_found", "unavailable", "The source endpoint was not found."),
            429: ("rate_limited", "rate_limited", "The source rate limit was reached."),
        }.get(exc.code, ("http_unavailable" if exc.code >= 500 else "http_error", "unavailable", "The source returned an HTTP failure."))
        raise SourceRequestError(code, message, outcome=outcome, status=exc.code) from None
    except (error.URLError, OSError) as exc:
        _record_unavailable(full_url, final_url, status)
        reason = exc.reason if isinstance(exc, error.URLError) else exc
        if isinstance(reason, socket.gaierror):
            raise SourceRequestError("dns_error", "The source hostname could not be resolved.") from None
        if isinstance(reason, ssl.SSLError):
            raise SourceRequestError("tls_error", "The source TLS connection could not be verified or established.") from None
        if isinstance(reason, TimeoutError):
            raise SourceRequestError("timeout", "The source request timed out.") from None
        raise SourceRequestError("connection_error", "The source connection failed; sensitive diagnostics are withheld.") from None


def _check_html_access_page(body: bytes, content_type: str) -> None:
    text = body[:16384].decode("utf-8", errors="ignore")
    if "html" not in content_type.lower() and not text.lstrip().lower().startswith(("<html", "<!doctype html")):
        return
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip().lower() if title_match else ""
    password = re.search(r"<input\b[^>]*\btype\s*=\s*['\"]?password\b", text, re.I)
    if password or re.search(r"^(?:sign\s*in|log\s*in|login|access denied|unauthori[sz]ed)(?:\s*[-|:]|$)", title):
        raise SourceRequestError("html_login", "The source returned an HTML authentication page.", outcome="unauthorized")
    if re.search(r"^(?:[45]\d\d\s+)?(?:error(?:\s+\d{3})?|not found|service unavailable|internal server error)(?:\s*[-|:]|$)", title):
        raise SourceRequestError("html_error", "The source returned an HTML error page.", outcome="unavailable")


def decode_source_text(body: bytes) -> str:
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        raise SourceRequestError("invalid_encoding", "The source response is not valid UTF-8 text.", outcome="invalid_response") from None


def decode_source_json(body: bytes | str, *, content_type: str = "", status: int = 200) -> Any:
    text = decode_source_text(body) if isinstance(body, bytes) else body
    if not text.strip() and status == 204:
        return None
    try:
        data = json.loads(text)
        mark_source_empty(data is None or data == [] or data == {} or data == "")
        return data
    except (json.JSONDecodeError, ValueError):
        code = "unexpected_html" if "html" in content_type.lower() or text.lstrip().startswith("<") else "malformed_json"
        raise SourceRequestError(code, "The source did not return the expected JSON response.", outcome="invalid_response", status=status) from None


def http_get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_origins: tuple[str, ...] | None = None,
) -> tuple[Any, str]:
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)
    body, response_headers, status, full_url = http_get(url, params=params, headers=merged_headers, timeout=timeout, allowed_origins=allowed_origins)
    return decode_source_json(body, content_type=response_headers.get("Content-Type", ""), status=status), full_url


def write_raw(
    payload: Any,
    *,
    requested: bool,
    raw_output_path: str | None = None,
    default_name: str = "raw-output.json",
) -> str | None:
    if not requested:
        return None
    target = Path(raw_output_path) if raw_output_path else Path.cwd() / default_name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(redact_credentials(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(target)


def getenv_any(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def run_source_cli(main, *, source: str | None = None) -> None:
    """Give one CLI run an isolated request ledger and safe typed failures."""
    ledger = _RETRIEVALS.set([])
    context = _SOURCE.set({"source": source} if source else {})
    try:
        main()
    except SourceRequestError as exc:
        emit(exc.as_result())
    except SourcePolicyError as exc:
        emit(result_error(exc.code, str(exc), outcome="refused", **(_SOURCE.get() or {})))
    except Exception:
        emit(result_error("request_failed", "Source request failed; sensitive diagnostics are withheld.", outcome="failure", **(_SOURCE.get() or {})))
    finally:
        _SOURCE.reset(context)
        _RETRIEVALS.reset(ledger)
