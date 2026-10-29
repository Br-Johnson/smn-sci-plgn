from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from _common import resolve_source_url, load_input, source_retrievals, source_outcome, decode_source_json, decode_source_text, emit, http_get, run_source_cli
from _source_auth import SourcePolicyError


ALLOWED_ORIGINS = ("https://critfc.org", "https://www.critfc.org", "https://gis.critfc.org")


PAGE_URL = "https://critfc.org/fish-and-watersheds/fishery-science/data-resources/columbia-basin-salmon-and-steelhead-crosswalk-project/"
REST_ROOT = "https://gis.critfc.org/arcgis/rest/services"


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


def json_preview(data):
    if isinstance(data, dict):
        return {"keys": list(data.keys())[:20]}
    if isinstance(data, list):
        return {"count": len(data), "sample": data[:5]}
    return {"type": type(data).__name__}


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

    if action == "page":
        url = PAGE_URL
        params = payload.get("params") or {}
    elif action == "rest_root":
        url = REST_ROOT
        params = {"f": "pjson"}
        extra = payload.get("params") or {}
        params.update(extra)
    elif action == "request":
        url = payload.get("url") or payload.get("path")
        if not url:
            emit({"ok": False, "error": "missing_url", "detail": "request action requires url or path"})
            return
        url = resolve_source_url(url, "https://gis.critfc.org" if str(url).startswith("/arcgis") else "https://critfc.org")
        params = payload.get("params") or {}
    else:
        emit({"ok": False, "error": "invalid_action", "detail": "action must be page, rest_root, or request"})
        return

    body, final_url, content_type = fetch(url, params=params, timeout=timeout)

    if "json" in content_type.lower() or final_url.endswith("?f=pjson"):
        data = decode_source_json(body, content_type=content_type)
    else:
        data = body

    raw_output_path = None
    if payload.get("save_raw"):
        output_dir = Path(payload.get("raw_output_path") or ".")
        if output_dir.is_dir() or str(output_dir).endswith(("/", "\\")):
            output_dir.mkdir(parents=True, exist_ok=True)
            raw_output_path = str(output_dir / "critfc-crosswalk-raw.txt")
        else:
            output_dir.parent.mkdir(parents=True, exist_ok=True)
            raw_output_path = str(output_dir)
        Path(raw_output_path).write_text(body, encoding="utf-8")

    if isinstance(data, str):
        records = html_preview(data, final_url)
        summary = {"format": "html", "title": records.get("title"), "link_count": len(records.get("links", []))}
    else:
        records = data
        summary = json_preview(data)

    emit({
        "ok": True,
        "source": "CRITFC Crosswalk Project",
        "action": action,
        "url": final_url,
        "retrieval": source_retrievals(),
        "outcome": source_outcome(),
        "summary": summary,
        "records": records,
        "raw_output_path": raw_output_path,
        "warnings": warnings,
    })


if __name__ == "__main__":
    run_source_cli(main, source='CRITFC Crosswalk Project')
