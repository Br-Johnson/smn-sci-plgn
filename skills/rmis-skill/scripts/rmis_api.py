from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, load_input, result_error, write_raw


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
    if not params:
        return base
    if isinstance(params, str):
        query = params.lstrip("?")
        joiner = "&" if "?" in base else "?"
        return f"{base}{joiner}{query}"
    if isinstance(params, dict):
        query = parse.urlencode(
            [(key, value) for key, value in params.items() if value is not None],
            doseq=True,
        )
        if not query:
            return base
        joiner = "&" if "?" in base else "?"
        return f"{base}{joiner}{query}"
    raise ValueError("params must be a string, object, or null")


def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 20,
) -> tuple[int, bytes, dict[str, str], str]:
    payload = None
    request_headers = headers.copy() if headers else {}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers.items()), url
    except error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items()), url


def parse_json_response(status: int, body: bytes):
    text = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    return text, payload


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
    auth_token = payload.get("auth_token")

    api_key = None
    jwt_token = None
    if auth_mode == "api_key":
        api_key = auth_token or getenv_any("RMIS_API_KEY", "RMPC_API_KEY")
    elif auth_mode == "jwt":
        jwt_token = auth_token or getenv_any("RMIS_JWT")
    else:
        api_key = auth_token or getenv_any("RMIS_API_KEY", "RMPC_API_KEY")
        if not api_key:
            jwt_token = auth_token or getenv_any("RMIS_JWT")

    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["xapikey"] = api_key
    elif jwt_token:
        headers["Authorization"] = jwt_token
    else:
        warnings.append("no RMIS_API_KEY, RMPC_API_KEY, RMIS_JWT, or auth_token provided")
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
        email = payload.get("email") or getenv_any("RMIS_EMAIL")
        password = payload.get("password") or getenv_any("RMIS_PASSWORD")
        if not email or not password:
            emit(result_error("missing_credentials", "login requires email and password"))
            return
        body = {"email": email, "password": password, "jwt": bool(payload.get("jwt", False))}
        status, raw, _, url = fetch(f"{API_BASE}/bauth", method="POST", body=body, timeout=timeout)
        text, data = parse_json_response(status, raw)
        if status != 200 or not isinstance(data, dict):
            emit(
                result_error(
                    "http_error",
                    "RMIS login failed",
                    status=status,
                    url=url,
                    body_preview=text[:400],
                )
            )
            return
        emit(
            {
                "ok": True,
                "source": "RMIS API",
                "action": "login",
                "url": url,
                "token": data.get("token"),
                "token_type": "jwt" if body["jwt"] else "api_key_or_token",
            }
        )
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

    status, raw, _, final_url = fetch(url, headers=headers, timeout=timeout)
    text, data = parse_json_response(status, raw)

    if status != 200 or data is None:
        message = "RMIS request failed"
        if status == 401:
            message = "RMIS request was unauthorized; provide RMIS_API_KEY, RMPC_API_KEY, or RMIS_JWT"
        emit(
            result_error(
                "http_error",
                message,
                action=action,
                status=status,
                url=final_url,
                body_preview=text[:400],
                warnings=warnings,
            )
        )
        return

    raw_output_path = write_raw(
        data,
        requested=bool(payload.get("save_raw")),
        raw_output_path=payload.get("raw_output_path"),
        default_name="rmis-raw.json",
    )

    emit(
        {
            "ok": True,
            "source": "RMIS API",
            "action": action,
            "url": final_url,
            "summary": summarize(data),
            "records": data,
            "raw_output_path": raw_output_path,
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
