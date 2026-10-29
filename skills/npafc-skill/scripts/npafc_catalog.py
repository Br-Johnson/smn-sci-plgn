from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from _common import resolve_source_url, mark_source_empty, load_input, source_retrievals, source_outcome, decode_source_json, decode_source_text, SourceRequestError, emit, http_get, run_source_cli
from _source_auth import SourcePolicyError


ALLOWED_ORIGINS = ("https://data.npafc.org", "https://www.npafc.org", "https://npafc.org")

from _source_output import emit_source_result


API_BASE = "https://data.npafc.org/api/3/action"
STATS_URL = "https://www.npafc.org/statistics/"


def read_input():
    return load_input()


def fetch(url: str, params: dict | None = None, timeout: int = 20):
    body, headers, _, final_url = http_get(url, params=params, timeout=timeout,
        headers={"User-Agent": "smn-sci-plgn/1.0"}, allowed_origins=ALLOWED_ORIGINS)
    return decode_source_text(body), final_url, headers.get("Content-Type", "")


def html_preview(html: str, base_url: str) -> dict:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = unescape(title_match.group(1)).strip() if title_match else None
    text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(unescape(text).split())
    links = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        if href.startswith("javascript:") or href.startswith("#"):
            continue
        links.append(urljoin(base_url, href))
        if len(links) >= 12:
            break
    return {
        "title": title,
        "snippet": text[:600],
        "links": links,
    }


def api_call(endpoint: str, params: dict | None = None, timeout: int = 20):
    body, final_url, content_type = fetch(f"{API_BASE}/{endpoint}", params=params, timeout=timeout)
    data = decode_source_json(body, content_type=content_type)
    if not isinstance(data, dict) or not data.get("success") or "result" not in data:
        raise SourceRequestError("source_api_error", "The source API refused the catalogue request.", outcome="invalid_response")
    if endpoint == "package_search":
        mark_source_empty(not data["result"].get("results") and data["result"].get("count", 0) == 0)
    return data["result"], final_url, body, content_type


def search_summary(result: dict) -> dict:
    items = result.get("results") or []
    sample = []
    for item in items[:5]:
        if isinstance(item, dict):
            sample.append({
                "title": item.get("title"),
                "name": item.get("name"),
                "id": item.get("id"),
            })
        else:
            sample.append(item)
    return {
        "count": result.get("count", len(items)),
        "sample": sample,
    }


def dataset_summary(result: dict) -> dict:
    resources = result.get("resources") or []
    sample_resources = []
    for resource in resources[:5]:
        if isinstance(resource, dict):
            sample_resources.append({
                "name": resource.get("name"),
                "format": resource.get("format"),
                "url": resource.get("url"),
            })
    return {
        "title": result.get("title"),
        "name": result.get("name"),
        "resource_count": len(resources),
        "sample_resources": sample_resources,
    }


def resource_summary(result: dict) -> dict:
    return {
        "name": result.get("name"),
        "format": result.get("format"),
        "url": result.get("url"),
    }


def main() -> None:
    try:
        payload = read_input()
    except Exception as exc:
        emit({"ok": False, "error": "invalid_input", "detail": str(exc)})
        return

    if not isinstance(payload, dict):
        emit({"ok": False, "error": "invalid_input", "detail": "expected a JSON object"})
        return

    action = payload.get("action")
    timeout = int(payload.get("timeout_sec", 20))
    warnings: list[str] = []

    try:
        if action == "dataset_search":
            params = {"rows": int(payload.get("rows", 5))}
            if payload.get("q") is not None:
                params["q"] = payload.get("q")
            if payload.get("start") is not None:
                params["start"] = payload.get("start")
            if payload.get("sort") is not None:
                params["sort"] = payload.get("sort")
            extra = payload.get("params") or {}
            params.update(extra)
            result, final_url, raw_body, content_type = api_call("package_search", params=params, timeout=timeout)
            summary = search_summary(result)
            records = result
        elif action == "dataset_show":
            dataset_id = payload.get("id")
            if not dataset_id:
                emit({"ok": False, "error": "missing_id", "detail": "dataset_show requires id"})
                return
            result, final_url, raw_body, content_type = api_call("package_show", params={"id": dataset_id}, timeout=timeout)
            summary = dataset_summary(result)
            records = result
        elif action == "resource_show":
            resource_id = payload.get("id")
            if not resource_id:
                emit({"ok": False, "error": "missing_id", "detail": "resource_show requires id"})
                return
            result, final_url, raw_body, content_type = api_call("resource_show", params={"id": resource_id}, timeout=timeout)
            summary = resource_summary(result)
            records = result
        elif action == "statistics_page":
            raw_body, final_url, content_type = fetch(STATS_URL, params=payload.get("params") or {}, timeout=timeout)
            records = html_preview(raw_body, final_url)
            summary = {"format": "html", "title": records.get("title"), "link_count": len(records.get("links", []))}
        elif action == "request":
            url = payload.get("url") or payload.get("path")
            if not url:
                emit({"ok": False, "error": "missing_url", "detail": "request action requires url or path"})
                return
            url = resolve_source_url(url, "https://data.npafc.org" if str(url).startswith("/api/") else "https://www.npafc.org")
            raw_body, final_url, content_type = fetch(url, params=payload.get("params") or {}, timeout=timeout)
            if "json" in content_type.lower():
                records = decode_source_json(raw_body, content_type=content_type)
            else:
                records = html_preview(raw_body, final_url)
            summary = {"format": "json"} if "json" in content_type.lower() else {
                "format": "html",
                "title": records.get("title") if isinstance(records, dict) else None,
                "link_count": len(records.get("links", [])) if isinstance(records, dict) else 0,
            }
        else:
            emit({"ok": False, "error": "invalid_action", "detail": "action must be dataset_search, dataset_show, resource_show, statistics_page, or request"})
            return
    except (SourcePolicyError, SourceRequestError):
        raise

    emit_source_result({
        "ok": True,
        "source": "NPAFC",
        "action": action,
        "url": final_url,
        "retrieval": source_retrievals(),
        "outcome": source_outcome(),
        "summary": summary,
        "warnings": warnings,
    }, payload, records, default_name="npafc-raw.txt", raw_payload=raw_body)


if __name__ == "__main__":
    run_source_cli(main, source='NPAFC')
