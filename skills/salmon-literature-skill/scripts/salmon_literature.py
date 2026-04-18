from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, http_get_json, load_input, result_error, write_raw


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def build_query(query: str, species: str | None) -> str:
    if species and species.lower() not in query.lower():
        return f"({query}) AND ({species})"
    return query


def search_pubmed(query: str, retmax: int, mindate: str | None, maxdate: str | None, sort: str, timeout: int):
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "sort": sort,
        "tool": "salmon-science-research",
    }
    if mindate:
        params["mindate"] = mindate
        params["datetype"] = "pdat"
    if maxdate:
        params["maxdate"] = maxdate
        params["datetype"] = "pdat"

    data, url = http_get_json(f"{EUTILS}/esearch.fcgi", params=params, timeout=timeout)
    id_list = data.get("esearchresult", {}).get("idlist", [])
    return id_list, url, data


def summarize_pubmed(ids: list[str], timeout: int):
    if not ids:
        return {}, None
    params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json",
        "tool": "salmon-science-research",
    }
    data, url = http_get_json(f"{EUTILS}/esummary.fcgi", params=params, timeout=timeout)
    return data, url


def compact_records(summary: dict, ids: list[str]) -> list[dict]:
    result = []
    for pmid in ids:
        record = summary.get("result", {}).get(pmid)
        if not record:
            continue
        authors = [author.get("name") for author in record.get("authors", [])[:5] if author.get("name")]
        result.append(
            {
                "pmid": pmid,
                "title": record.get("title"),
                "pubdate": record.get("pubdate"),
                "source": record.get("source"),
                "authors": authors,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return result


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:
        emit(result_error("invalid_input", str(exc)))
        return

    if not isinstance(payload, dict):
        emit(result_error("invalid_input", "expected a JSON object"))
        return

    query = payload.get("query")
    if not query:
        emit(result_error("missing_query", "query is required"))
        return

    species = payload.get("species")
    retmax = int(payload.get("retmax", 5))
    timeout = int(payload.get("timeout_sec", 20))
    sort = payload.get("sort", "relevance")
    full_query = build_query(str(query), str(species) if species else None)

    ids, search_url, search_raw = search_pubmed(
        full_query,
        retmax=retmax,
        mindate=payload.get("mindate"),
        maxdate=payload.get("maxdate"),
        sort=sort,
        timeout=timeout,
    )
    summary_raw, summary_url = summarize_pubmed(ids, timeout)
    records = compact_records(summary_raw, ids)

    raw_payload = {
        "query": full_query,
        "search_url": search_url,
        "summary_url": summary_url,
        "search": search_raw,
        "summary": summary_raw,
    }
    raw_output_path = write_raw(
        raw_payload,
        requested=bool(payload.get("save_raw")),
        raw_output_path=payload.get("raw_output_path"),
        default_name="salmon-literature-raw.json",
    )

    emit(
        {
            "ok": True,
            "source": "PubMed via NCBI E-utilities",
            "query": full_query,
            "search_url": search_url,
            "summary_url": summary_url,
            "result_count": len(records),
            "records": records,
            "raw_output_path": raw_output_path,
        }
    )


if __name__ == "__main__":
    main()
