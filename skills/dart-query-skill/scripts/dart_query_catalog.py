from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, http_get, load_input, result_error


BASE_URL = "https://www.cbr.washington.edu"

CATALOG = {
    "adult_passage_counts": {
        "path": "/dart/query/adult_graph_text",
        "lane": "adult passage",
        "description": "Adult salmonid passage counts.",
    },
    "juvenile_pit_observations": {
        "path": "/dart/query/pit_obs_graph_text",
        "lane": "juvenile passage",
        "description": "Juvenile PIT tag observations.",
    },
    "river_environment": {
        "path": "/dart/query/river_graph_text",
        "lane": "river conditions",
        "description": "River environment conditions and context.",
    },
    "streamflow": {
        "path": "/dart/query/streamflow_graph_text",
        "lane": "river conditions",
        "description": "Streamflow data surfaces.",
    },
    "basin_conditions": {
        "path": "/dart/query/basin_conditions",
        "lane": "basin conditions",
        "description": "Basin-scale conditions page.",
    },
    "upwelling": {
        "path": "/dart/query/upwell_graph_text",
        "lane": "ocean conditions",
        "description": "Coastal upwelling index.",
    },
    "hatchery_releases": {
        "path": "/dart/query/hatch",
        "lane": "hatchery context",
        "description": "Hatchery releases query surface.",
    },
    "pit_releases": {
        "path": "/dart/query/pit_releases",
        "lane": "release metadata",
        "description": "PIT tag release information.",
    },
}


def title_from_html(html: str) -> str | None:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def description_from_html(html: str) -> str | None:
    paragraphs = re.findall(r"<p>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
    for paragraph in paragraphs:
        text = re.sub(r"<.*?>", " ", paragraph)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 40:
            return text[:400]
    return None


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:
        emit(result_error("invalid_input", str(exc)))
        return

    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    action = payload.get("action", "catalog")
    if action == "catalog":
        emit(
            {
                "ok": True,
                "source": "Columbia River DART",
                "action": "catalog",
                "entries": CATALOG,
            }
        )
        return

    if action != "page":
        emit(result_error("invalid_action", "action must be catalog or page"))
        return

    name = payload.get("name")
    path = payload.get("path")
    entry = CATALOG.get(name) if name else None
    if not path and entry:
        path = entry["path"]
    if not path:
        emit(result_error("missing_path", "page action requires name or path"))
        return
    full_url = f"{BASE_URL}{path}" if str(path).startswith("/") else str(path)

    body, _, _, url = http_get(full_url, timeout=int(payload.get("timeout_sec", 20)))
    html = body.decode("utf-8", errors="replace")

    emit(
        {
            "ok": True,
            "source": "Columbia River DART",
            "action": "page",
            "url": url,
            "title": title_from_html(html),
            "description": description_from_html(html),
            "matched_catalog_entry": entry,
        }
    )


if __name__ == "__main__":
    main()
