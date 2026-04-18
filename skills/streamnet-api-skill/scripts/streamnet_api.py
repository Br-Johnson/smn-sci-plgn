from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, http_get_json, load_input, result_error, write_raw


BASE_URL = "https://api.streamnet.org"


def summarize(action: str, data):
    if action == "tables" and isinstance(data, list):
        sample = data[:10]
        return {
            "table_count": len(data),
            "sample": sample,
        }
    if action == "records" and isinstance(data, list):
        return {"record_count": len(data), "sample": data[:5]}
    if isinstance(data, dict):
        keys = list(data.keys())[:20]
        return {"keys": keys}
    return {"type": type(data).__name__}


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
    if action not in {"tables", "table", "records", "request"}:
        emit(result_error("invalid_action", "action must be one of tables, table, records, request"))
        return

    headers = {}
    api_key = payload.get("api_key") or getenv_any("STREAMNET_API_KEY")
    warnings = []
    if api_key:
        headers["XApiKey"] = api_key
    else:
        warnings.append("no STREAMNET_API_KEY provided; authenticated calls will likely fail")

    timeout = int(payload.get("timeout_sec", 20))

    if action == "tables":
        path = "/api/v1/ca/tables"
        params = payload.get("params") or {}
    elif action == "table":
        table_id = payload.get("table_id")
        if not table_id:
            emit(result_error("missing_table_id", "table action requires table_id"))
            return
        path = f"/api/v1/ca/tables/{table_id}"
        params = payload.get("params") or {}
    elif action == "records":
        record_id = payload.get("record_id")
        if record_id:
            path = f"/api/v1/ca/{record_id}"
            params = payload.get("params") or {}
        else:
            path = "/api/v1/ca"
            params = payload.get("params") or {}
            for key in ("table_id", "page", "per_page", "agency", "updated_since"):
                if payload.get(key) is not None:
                    params[key] = payload.get(key)
    else:
        req_path = payload.get("path")
        if not req_path:
            emit(result_error("missing_path", "request action requires path"))
            return
        path = req_path if str(req_path).startswith("/") else f"/{req_path}"
        params = payload.get("params") or {}

    url = f"{BASE_URL}{path}"
    try:
        data, full_url = http_get_json(url, params=params, headers=headers, timeout=timeout)
    except RuntimeError as exc:
        detail = json.loads(str(exc))
        message = "StreamNet request failed"
        if detail.get("status") == 401:
            message = "StreamNet request was unauthorized; check STREAMNET_API_KEY"
        emit(
            result_error(
                "http_error",
                message,
                action=action,
                status=detail.get("status"),
                url=detail.get("url"),
                body_preview=detail.get("body", "")[:300],
                warnings=warnings,
            )
        )
        return

    raw_output_path = write_raw(
        data,
        requested=bool(payload.get("save_raw")),
        raw_output_path=payload.get("raw_output_path"),
        default_name="streamnet-raw.json",
    )

    emit(
        {
            "ok": True,
            "source": "StreamNet REST API",
            "action": action,
            "url": full_url,
            "summary": summarize(action, data),
            "records": data if action in {"table", "request"} else None,
            "raw_output_path": raw_output_path,
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
