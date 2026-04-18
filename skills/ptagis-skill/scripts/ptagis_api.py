from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, getenv_any, http_get_json, load_input, result_error, write_raw


BASE_URL = "https://api.ptagis.org"


VALIDATION_KIND_TO_PATH = {
    "all": "/ValidationCodes",
    "mrr_codes": "/ValidationCodes/MrrCodes",
    "mrr_projects": "/ValidationCodes/MrrProjects",
    "mrr_projects_active": "/ValidationCodes/MrrProjects/Active",
    "mrr_sites": "/ValidationCodes/MrrSites",
    "tag_masks": "/ValidationCodes/TagMasks",
    "revision_date": "/ValidationCodes/RevisionDate",
}


def summarize(action: str, data):
    if isinstance(data, list):
        return {"count": len(data), "sample": data[:5]}
    if isinstance(data, dict):
        return {"keys": list(data.keys())[:20]}
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
    timeout = int(payload.get("timeout_sec", 20))

    if action == "site_observations":
        site_code = payload.get("site_code")
        year = payload.get("year")
        if not site_code or year is None:
            emit(result_error("missing_fields", "site_observations requires site_code and year"))
            return
        path = f"/data/interrogation/site/{site_code}/year/{year}/observations"
        params = payload.get("params") or {}
    elif action == "interrogation_site_codes":
        path = "/eventlogs/interrogation/sitecodes/ptagis"
        params = payload.get("params") or {}
    elif action == "interrogation_files":
        site_code = payload.get("site_code")
        project_code = payload.get("project_code")
        year = payload.get("year")
        if project_code and year is not None:
            path = f"/files/mrr/sites/{project_code}/year/{year}"
        elif site_code and year is not None:
            path = f"/files/interrogation/sites/{site_code}/year/{year}"
        elif site_code:
            path = f"/files/interrogation/sites/{site_code}"
        else:
            path = "/files/interrogation/sites"
        params = payload.get("params") or {}
    elif action == "validation_codes":
        kind = payload.get("kind", "all")
        path = VALIDATION_KIND_TO_PATH.get(kind)
        if not path:
            emit(result_error("invalid_kind", f"unsupported validation kind: {kind}"))
            return
        domain = payload.get("domain")
        if kind == "mrr_codes" and domain:
            path = f"/ValidationCodes/MrrCodes/{domain}"
        params = payload.get("params") or {}
    elif action == "reports":
        user_name = payload.get("user_name")
        if not user_name:
            emit(result_error("missing_user_name", "reports action requires user_name"))
            return
        path = f"/reporting/reports/{user_name}"
        params = payload.get("params") or {}
    elif action == "report_file":
        user_name = payload.get("user_name")
        report_name = payload.get("report_name")
        if not user_name or not report_name:
            emit(result_error("missing_fields", "report_file requires user_name and report_name"))
            return
        path = f"/reporting/reports/{user_name}/file/{report_name}"
        params = payload.get("params") or {}
    elif action == "request":
        req_path = payload.get("path")
        if not req_path:
            emit(result_error("missing_path", "request action requires path"))
            return
        path = req_path if str(req_path).startswith("/") else f"/{req_path}"
        params = payload.get("params") or {}
    else:
        emit(result_error("invalid_action", "unsupported PTAGIS action"))
        return

    headers = {}
    token = payload.get("auth_token") or getenv_any("PTAGIS_API_TOKEN", "PTAGIS_API_KEY")
    warnings = []
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        warnings.append("no PTAGIS auth token provided; some endpoints may reject the request")

    url = f"{BASE_URL}{path}"
    try:
        data, full_url = http_get_json(url, params=params, headers=headers, timeout=timeout)
    except RuntimeError as exc:
        detail = json.loads(str(exc))
        message = "PTAGIS request failed"
        if detail.get("status") in {401, 403}:
            message = "PTAGIS request was unauthorized; check PTAGIS_API_TOKEN or PTAGIS_API_KEY"
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
        default_name="ptagis-raw.json",
    )

    emit(
        {
            "ok": True,
            "source": "PTAGIS API",
            "action": action,
            "url": full_url,
            "summary": summarize(action, data),
            "records": data,
            "raw_output_path": raw_output_path,
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
