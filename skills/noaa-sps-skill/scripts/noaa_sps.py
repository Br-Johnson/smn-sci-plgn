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


ALLOWED_ORIGINS = ("https://www.webapps.nwfsc.noaa.gov", "https://webapps.nwfsc.noaa.gov", "https://www.fisheries.noaa.gov")


HOME_URL = "https://www.webapps.nwfsc.noaa.gov/sps"
METADATA_URL = "https://www.fisheries.noaa.gov/inport/item/17904"
HELP_URL = "https://www.webapps.nwfsc.noaa.gov/appim/appthemes/spspub2.0/public/Help/%21SSL%21/WebHelp/introduction.htm"


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

    if action == "home":
        url = HOME_URL
        params = payload.get("params") or {}
    elif action == "help":
        url = HELP_URL
        params = payload.get("params") or {}
    elif action == "metadata":
        url = METADATA_URL
        params = {}
    elif action == "request":
        url = payload.get("url") or payload.get("path")
        if not url:
            emit({"ok": False, "error": "missing_url", "detail": "request action requires url or path"})
            return
        url = resolve_source_url(url, "https://www.webapps.nwfsc.noaa.gov")
        params = payload.get("params") or {}
    else:
        emit({"ok": False, "error": "invalid_action", "detail": "action must be home, help, metadata, or request"})
        return

    body, final_url, content_type = fetch(url, params=params, timeout=timeout)

    if "json" in content_type.lower():
        data = decode_source_json(body, content_type=content_type)
    else:
        data = body

    raw_output_path = None
    if payload.get("save_raw"):
        output_path = Path(payload.get("raw_output_path") or "noaa-sps-raw.txt")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(body, encoding="utf-8")
        raw_output_path = str(output_path)

    if isinstance(data, str):
        records = html_preview(data, final_url)
        summary = {"format": "html", "title": records.get("title"), "link_count": len(records.get("links", []))}
    else:
        records = data
        summary = json_preview(data)

    emit({
        "ok": True,
        "source": "NOAA SPS",
        "action": action,
        "discovery_scope": "owner_metadata_only" if action == "metadata" else "source_response_only",
        "url": final_url,
        "retrieval": source_retrievals(),
        "outcome": source_outcome(),
        "summary": summary,
        "records": records,
        "raw_output_path": raw_output_path,
        "warnings": warnings,
    })


if __name__ == "__main__":
    run_source_cli(main, source='NOAA SPS', owner_documentation=METADATA_URL)
