"""Bounded source-CLI previews; no retrieval or credential policy lives here."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from _source_auth import redact_credentials
from _common import write_raw

MAX_ROWS = 5
MAX_BYTES = 16_384


def _record_count(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("records", "results", "resources"):
            if isinstance(data.get(key), list):
                return len(data[key])
        return int(bool(data))
    return int(data is not None)


def _preview(value: Any, *, text: int, items: int, keys: int, depth: int = 0):
    if depth > 5:
        return None, True
    if isinstance(value, str):
        return value[:text], len(value) > text
    if isinstance(value, (dict, list)):
        pairs = list(value.items()) if isinstance(value, dict) else list(enumerate(value))
        if isinstance(value, dict):
            # CKAN metadata can precede its resource collection by many fields.
            # Retain the primary rows before applying the object-width budget.
            primary = next((key for key in ("records", "results", "resources") if isinstance(value.get(key), list)), None)
            pairs.sort(key=lambda pair: pair[0] != primary)
        limit = keys if isinstance(value, dict) else items
        output = {} if isinstance(value, dict) else []
        truncated = len(pairs) > limit
        for key, item in pairs[:limit]:
            shown, changed = _preview(item, text=text, items=items, keys=keys, depth=depth + 1)
            truncated |= changed
            if isinstance(output, dict):
                rendered_key = key[:160]
                truncated |= rendered_key != key
                output[rendered_key] = shown
            else:
                output.append(shown)
        return output, truncated
    return value, False


def _serialize(result: dict) -> str:
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def emit_source_result(result: dict, request: dict, data: Any, *, default_name: str, raw_payload: Any = None) -> None:
    """Emit a redacted preview with a hard bound on actual serialized stdout."""
    result = dict(result)
    summary = dict(result.get("summary") or {})
    # Records appear once. Source-specific metadata and totals remain useful.
    summary.pop("sample", None)
    summary.pop("sample_resources", None)
    result["summary"] = summary
    result["records"] = data
    result.setdefault("raw_output_path", None)
    if request.get("save_raw"):
        try:
            raw = data if raw_payload is None else raw_payload
            if isinstance(raw_payload, str):
                try:
                    raw = json.loads(raw_payload)
                except ValueError:
                    target = Path(request.get("raw_output_path") or default_name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(redact_credentials(raw_payload), encoding="utf-8")
                    result["raw_output_path"] = str(target)
                else:
                    result["raw_output_path"] = write_raw(raw, requested=True, raw_output_path=request.get("raw_output_path"), default_name=default_name)
            else:
                result["raw_output_path"] = write_raw(raw, requested=True, raw_output_path=request.get("raw_output_path"), default_name=default_name)
        except (OSError, ValueError, TypeError):
            result.update(ok=False, retrieval_ok=True, raw_output_path=None,
                          error={"code": "raw_output_failed", "message": "Source retrieval succeeded, but saving local raw output failed. Choose a writable file path; compact findings are retained."})
    result = redact_credentials(result)
    count = _record_count(data)
    if request.get("raw_stdout") is True:
        result["output"] = {"mode": "raw", "record_count": count, "preview_count": count,
                            "truncated": False, "max_rows": None, "max_bytes": None}
        sys.stdout.write(_serialize(result))
        return
    for text, items, keys in ((512, 5, 20), (256, 5, 20), (128, 5, 12), (64, 5, 8), (32, 1, 6)):
        preview = {}
        truncated = False
        for key, value in result.items():
            preview[key], changed = _preview(value, text=text, items=items, keys=keys)
            truncated |= changed
        preview["output"] = {
            "mode": "preview", "max_rows": MAX_ROWS, "max_bytes": MAX_BYTES,
            "record_count": count, "preview_count": _record_count(preview["records"]),
            "truncated": truncated,
        }
        rendered = _serialize(preview)
        if len(rendered.encode("utf-8")) <= MAX_BYTES:
            sys.stdout.write(rendered)
            return
    # A pathological nested response still yields a small useful receipt.
    preview = {key: str(result.get(key, ""))[:512] for key in ("source", "action", "url")}
    preview.update(ok=result.get("ok", True), summary={"count": count}, records=None,
                   raw_output_path=str(result["raw_output_path"])[:512] if result.get("raw_output_path") else None,
                   output={"mode": "preview", "max_rows": MAX_ROWS, "max_bytes": MAX_BYTES,
                           "record_count": count, "preview_count": 0, "truncated": True})
    for key in ("error", "retrieval_ok", "retrieval"):
        if key in result:
            preview[key], _ = _preview(result[key], text=128, items=1, keys=8)
    rendered = _serialize(preview)
    if len(rendered.encode("utf-8")) > MAX_BYTES:
        # The source URL remains as provenance even if a very large retrieval
        # history cannot fit alongside the compact failure/summary receipt.
        preview["retrieval"] = {"truncated": True}
        rendered = _serialize(preview)
    sys.stdout.write(rendered)
