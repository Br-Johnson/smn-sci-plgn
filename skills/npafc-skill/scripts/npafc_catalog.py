from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


API_BASE = "https://data.npafc.org/api/3/action"
STATS_URL = "https://www.npafc.org/statistics/"


def emit(payload) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    sys.stdout.write("\n")


def read_input():
    raw = sys.stdin.read()
    return json.loads(raw)


def fetch(url: str, params: dict | None = None, timeout: int = 20):
    if params:
        query = urlencode(params, doseq=True)
        url = f"{url}{'&' if '?' in url else '?'}{query}"
    request = Request(url, headers={"User-Agent": "smn-sci-plgn/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        body = exc.read() if exc.fp else b""
        raise RuntimeError(json.dumps({
            "status": exc.code,
            "url": exc.geturl() or url,
            "body": body.decode("utf-8", "replace"),
        })) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(json.dumps({"status": None, "url": url, "body": str(exc)})) from exc
    return body.decode("utf-8", "replace"), final_url, content_type


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
    if "json" not in content_type.lower() and not body.lstrip().startswith(("{", "[")):
        raise RuntimeError(json.dumps({"status": None, "url": final_url, "body": body}))
    data = json.loads(body)
    if not isinstance(data, dict) or not data.get("success"):
        raise RuntimeError(json.dumps({"status": None, "url": final_url, "body": body}))
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
            if not str(url).startswith(("http://", "https://")):
                if str(url).startswith("/api/"):
                    url = f"https://data.npafc.org{url}"
                else:
                    url = f"https://www.npafc.org/{str(url).lstrip('/')}"
            raw_body, final_url, content_type = fetch(url, params=payload.get("params") or {}, timeout=timeout)
            if "json" in content_type.lower():
                try:
                    records = json.loads(raw_body)
                except Exception:
                    records = raw_body
            else:
                records = html_preview(raw_body, final_url)
            summary = json_preview(records) if "json" in content_type.lower() else {
                "format": "html",
                "title": records.get("title") if isinstance(records, dict) else None,
                "link_count": len(records.get("links", [])) if isinstance(records, dict) else 0,
            }
        else:
            emit({"ok": False, "error": "invalid_action", "detail": "action must be dataset_search, dataset_show, resource_show, statistics_page, or request"})
            return
    except RuntimeError as exc:
        detail = json.loads(str(exc))
        emit({
            "ok": False,
            "source": "NPAFC",
            "action": action,
            "error": "http_error",
            "detail": "NPAFC request failed",
            "status": detail.get("status"),
            "url": detail.get("url"),
            "body_preview": str(detail.get("body", ""))[:300],
            "warnings": warnings,
        })
        return

    raw_output_path = None
    if payload.get("save_raw"):
        output_path = Path(payload.get("raw_output_path") or "npafc-raw.txt")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(raw_body if isinstance(raw_body, str) else json.dumps(raw_body, ensure_ascii=True, indent=2), encoding="utf-8")
        raw_output_path = str(output_path)

    emit({
        "ok": True,
        "source": "NPAFC",
        "action": action,
        "url": final_url,
        "summary": summary,
        "records": records,
        "raw_output_path": raw_output_path,
        "warnings": warnings,
    })


if __name__ == "__main__":
    main()
