from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


HOME_URL = "https://www.webapps.nwfsc.noaa.gov/sps/"
HELP_URL = "https://www.webapps.nwfsc.noaa.gov/appim/appthemes/spspub2.0/public/Help/%21SSL%21/WebHelp/introduction.htm"


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
    elif action == "request":
        url = payload.get("url") or payload.get("path")
        if not url:
            emit({"ok": False, "error": "missing_url", "detail": "request action requires url or path"})
            return
        if not str(url).startswith(("http://", "https://")):
            url = f"https://www.webapps.nwfsc.noaa.gov/{str(url).lstrip('/')}"
        params = payload.get("params") or {}
    else:
        emit({"ok": False, "error": "invalid_action", "detail": "action must be home, help, or request"})
        return

    try:
        body, final_url, content_type = fetch(url, params=params, timeout=timeout)
    except RuntimeError as exc:
        detail = json.loads(str(exc))
        emit({
            "ok": False,
            "source": "NOAA SPS",
            "action": action,
            "error": "http_error",
            "detail": "SPS request failed",
            "status": detail.get("status"),
            "url": detail.get("url"),
            "body_preview": str(detail.get("body", ""))[:300],
            "warnings": warnings,
        })
        return

    if "json" in content_type.lower():
        try:
            data = json.loads(body)
        except Exception:
            data = body
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
        "url": final_url,
        "summary": summary,
        "records": records,
        "raw_output_path": raw_output_path,
        "warnings": warnings,
    })


if __name__ == "__main__":
    main()
