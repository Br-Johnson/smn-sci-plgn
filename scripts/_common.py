from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from _source_auth import SourcePolicyError, authenticated_headers, contains_inline_credentials, redact_credentials, source_urlopen


DEFAULT_TIMEOUT = 20


def load_input() -> Any:
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("expected JSON on stdin")
    return json.loads(raw)


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


def build_url(base_url: str, params: dict[str, Any] | None = None) -> str:
    if not params:
        return base_url
    query = parse.urlencode(
        [(key, value) for key, value in params.items() if value is not None],
        doseq=True,
    )
    return f"{base_url}?{query}"


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
    try:
        with source_urlopen(req, timeout=timeout, allowed_origins=allowed_origins) as response:
            return (
                response.read(),
                dict(response.headers.items()),
                response.status,
                full_url,
            )
    except error.HTTPError as exc:
        body = b"" if authenticated_headers(headers) else exc.read()
        headers_map = redact_credentials(dict(exc.headers.items()))
        raise RuntimeError(
            json.dumps(redact_credentials(
                {
                    "status": exc.code,
                    "url": full_url,
                    "body": body.decode("utf-8", errors="replace"),
                    "headers": headers_map,
                }
            ))
        ) from None


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
    body, _, _, full_url = http_get(url, params=params, headers=merged_headers, timeout=timeout, allowed_origins=allowed_origins)
    return json.loads(body.decode("utf-8")), full_url


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


def run_source_cli(main) -> None:
    """Keep exception details out of agent-visible source command output."""
    try:
        main()
    except SourcePolicyError as exc:
        emit(result_error(exc.code, str(exc)))
    except Exception:
        emit(result_error(
            "request_failed",
            "Source request failed. Check the request fields, local credential setup and source availability; sensitive diagnostics are not emitted.",
        ))
