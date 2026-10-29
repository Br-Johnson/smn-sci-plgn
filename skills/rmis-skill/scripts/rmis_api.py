from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import build_url as build_source_url, source_retrievals, source_outcome, decode_source_json, decode_source_text, http_get, SourceRequestError, run_source_cli, inline_credentials_refused, emit, getenv_any, load_input, result_error
from _source_output import emit_source_result


API_BASE = "https://phish.rmis.org"
ANNOUNCE_URL = "https://www.rmis.org/include/rmis_announce.html"

ACTION_TO_PATH = {
    "release": "/release",
    "recovery": "/recovery",
    "location": "/location",
    "catchsample": "/catchsample",
    "description": "/description",
    "files": "/files",
}


def build_url(base: str, params) -> str:
    return build_source_url(base, params)


def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 20,
    allowed_origins: tuple[str, ...] | None = None,
) -> tuple[int, bytes, dict[str, str], str]:
    if method != "GET" or body is not None:
        raise SourceRequestError("unsupported_method", "This source adapter performs read-only requests.", outcome="refused")
    raw, response_headers, status, final_url = http_get(url, headers=headers, timeout=timeout,
        allowed_origins=allowed_origins or ("https://www.rmis.org", "https://rmis.org"))
    return status, raw, response_headers, final_url


def parse_json_response(status: int, body: bytes):
    text = decode_source_text(body)
    return text, decode_source_json(text, status=status)


def summarize(data):
    if isinstance(data, dict):
        if "records" in data and isinstance(data["records"], list):
            return {
                "totalCount": data.get("totalCount"),
                "count": data.get("count", len(data["records"])),
                "page": data.get("page"),
                "sample": data["records"][:5],
            }
        return {"keys": list(data.keys())[:20]}
    if isinstance(data, list):
        return {"count": len(data), "sample": data[:5]}
    return {"type": type(data).__name__}


def resolve_auth_headers(payload: dict) -> tuple[dict[str, str], list[str]]:
    warnings = []
    auth_mode = payload.get("auth_mode")

    api_key = None
    jwt_token = None
    if auth_mode == "api_key":
        api_key = getenv_any("RMIS_API_KEY", "RMPC_API_KEY")
    elif auth_mode == "jwt":
        jwt_token = getenv_any("RMIS_JWT")
    else:
        api_key = getenv_any("RMIS_API_KEY", "RMPC_API_KEY")
        if not api_key:
            jwt_token = getenv_any("RMIS_JWT")

    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["xapikey"] = api_key
    elif jwt_token:
        headers["Authorization"] = jwt_token
    else:
        warnings.append("no RMIS_API_KEY, RMPC_API_KEY or RMIS_JWT configured in the local environment")
    return headers, warnings


def fetch_announcement(timeout: int) -> dict:
    status, body, _, url = fetch(ANNOUNCE_URL, timeout=timeout)
    text = body.decode("utf-8", errors="replace")
    version_match = re.search(
        r"Version\s+([0-9]+\.[0-9]+)\s+of the RMIS Database",
        text,
        flags=re.IGNORECASE,
    )
    date_match = re.search(r"as of:\s*(.+?)\.", text, flags=re.IGNORECASE | re.DOTALL)
    effective_date = None
    if date_match:
        effective_date = re.sub(r"<[^>]+>", "", date_match.group(1))
        effective_date = " ".join(effective_date.split()) or None
    return {
        "ok": status == 200,
        "source": "RMIS announcement page",
        "url": url,
        "current_version": version_match.group(1) if version_match else None,
            "retrieval": source_retrievals(),
            "outcome": source_outcome(),
        "effective_date": effective_date,
        "status_code": status,
    }


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:
        emit(result_error("invalid_input", str(exc)))
        return

    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    action = payload.get("action")
    timeout = int(payload.get("timeout_sec", 20))

    if action == "announcement":
        emit(fetch_announcement(timeout))
        return

    if action == "login":
        emit(result_error(
            "local_auth_required",
            "Authenticate in your own terminal or the source portal, then use an environment credential. Never submit a password or key through chat.",
        ))
        return

    if inline_credentials_refused(payload):
        return

    if action not in set(ACTION_TO_PATH) | {"request"}:
        emit(
            result_error(
                "invalid_action",
                "action must be one of announcement, login, release, recovery, location, catchsample, description, files, request",
            )
        )
        return

    headers, warnings = resolve_auth_headers(payload)
    if action == "request":
        path = payload.get("path")
        if not path:
            emit(result_error("missing_path", "request action requires path"))
            return
        path = path if str(path).startswith("/") else f"/{path}"
    else:
        path = ACTION_TO_PATH[action]

    try:
        url = build_url(f"{API_BASE}{path}", payload.get("params"))
    except ValueError as exc:
        emit(result_error("invalid_params", str(exc)))
        return

    status, raw, _, final_url = fetch(url, headers=headers, timeout=timeout, allowed_origins=(API_BASE,))
    text, data = parse_json_response(status, raw)


    emit_source_result(
        {
            "ok": True,
            "source": "RMIS API",
            "action": action,
            "url": final_url,
            "retrieval": source_retrievals(),
            "outcome": source_outcome(),
            "summary": summarize(data),
            "warnings": warnings,
        }, payload, data, default_name="rmis-raw.json",
    )


if __name__ == "__main__":
    run_source_cli(main, source='RMIS API')
