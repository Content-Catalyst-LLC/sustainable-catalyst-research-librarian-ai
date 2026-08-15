from __future__ import annotations

"""Federated external discovery contracts for Research Librarian v8.0.0.

External discovery is a research lead layer, not Sustainable Catalyst editorial
content and not verified evidence. Provider identity, record identifiers, access
metadata, and normalization provenance remain attached to every result. Results
enter My Library only through an explicit authenticated save action.
"""

from datetime import datetime, timezone
import hashlib
import html
import json
import re
from typing import Any
from urllib.parse import quote, urlparse
import uuid
import xml.etree.ElementTree as ET

import httpx

FEDERATED_PROVIDER_CATALOG_SCHEMA = "sc-federated-provider-catalog/1.0"
FEDERATED_SEARCH_SCHEMA = "sc-federated-research-search/1.0"
FEDERATED_RESULT_SCHEMA = "sc-federated-research-result/1.0"
FEDERATED_IMPORT_SCHEMA = "sc-federated-library-import/1.0"
FEDERATED_SEARCH_SUMMARY_SCHEMA = "sc-federated-search-summary/1.0"

PROVIDERS: dict[str, dict[str, Any]] = {
    "openalex": {
        "label": "OpenAlex",
        "kind": "scholarly-graph",
        "base_url": "https://api.openalex.org",
        "search_path": "/works",
        "response_format": "json",
        "auth": "optional-api-key",
        "supports": ["articles", "books", "datasets", "theses"],
        "official_docs": "https://developers.openalex.org/api-reference/works",
    },
    "crossref": {
        "label": "Crossref",
        "kind": "scholarly-metadata",
        "base_url": "https://api.crossref.org",
        "search_path": "/works",
        "response_format": "json",
        "auth": "none",
        "supports": ["articles", "books", "proceedings", "datasets", "reports"],
        "official_docs": "https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
    },
    "europe-pmc": {
        "label": "Europe PMC",
        "kind": "biomedical-literature",
        "base_url": "https://www.ebi.ac.uk/europepmc/webservices/rest",
        "search_path": "/search",
        "response_format": "json",
        "auth": "none",
        "supports": ["articles", "preprints", "books", "patents"],
        "official_docs": "https://europepmc.org/RestfulWebService",
    },
    "open-library": {
        "label": "Open Library",
        "kind": "book-catalog",
        "base_url": "https://openlibrary.org",
        "search_path": "/search.json",
        "response_format": "json",
        "auth": "none",
        "supports": ["books", "editions", "authors"],
        "official_docs": "https://openlibrary.org/developers/api",
    },
    "arxiv": {
        "label": "arXiv",
        "kind": "preprint-repository",
        "base_url": "https://export.arxiv.org",
        "search_path": "/api/query",
        "response_format": "atom",
        "auth": "none",
        "supports": ["preprints"],
        "official_docs": "https://info.arxiv.org/help/api/user-manual.html",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _text(value: Any, limit: int = 4000) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    raw = re.sub(r"<[^>]+>", " ", str(value or ""))
    clean = re.sub(r"\s+", " ", html.unescape(raw)).strip()
    return clean[:limit]


def _url(value: Any, limit: int = 2000) -> str:
    clean = _text(value, limit)
    if not clean:
        return ""
    parsed = urlparse(clean)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return clean


def _authors(value: Any, limit: int = 30) -> list[str]:
    rows: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = item.get("display_name") or item.get("name") or item.get("fullName") or item.get("authorString")
            else:
                name = item
            clean = _text(name, 300)
            if clean and clean not in rows:
                rows.append(clean)
            if len(rows) >= limit:
                break
    elif value:
        for item in str(value).split(","):
            clean = _text(item, 300)
            if clean and clean not in rows:
                rows.append(clean)
            if len(rows) >= limit:
                break
    return rows


def _doi(value: Any) -> str:
    clean = _text(value, 500).lower()
    clean = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", clean)
    clean = re.sub(r"^doi:\s*", "", clean)
    return clean


def _isbn(value: Any) -> str:
    clean = re.sub(r"[^0-9Xx]", "", _text(value, 80)).upper()
    return clean if len(clean) in {10, 13} else ""


def _year(value: Any) -> str:
    match = re.search(r"(?:18|19|20|21)\d{2}", _text(value, 80))
    return match.group(0) if match else ""


def _canonical_key(result: dict[str, Any]) -> str:
    ids = result.get("identifiers") if isinstance(result.get("identifiers"), dict) else {}
    if ids.get("doi"):
        return "doi:" + str(ids["doi"]).lower()
    if ids.get("arxiv"):
        return "arxiv:" + str(ids["arxiv"]).lower()
    isbns = ids.get("isbn") if isinstance(ids.get("isbn"), list) else []
    if isbns:
        return "isbn:" + str(isbns[0]).upper()
    seed = "|".join([
        re.sub(r"[^a-z0-9]+", " ", str(result.get("title") or "").lower()).strip(),
        str(result.get("published_year") or ""),
        str((result.get("authors") or [""])[0]).lower(),
    ])
    return "meta:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _result(provider_id: str, provider_record_id: str, **fields: Any) -> dict[str, Any]:
    provider = PROVIDERS[provider_id]
    row = {
        "schema": FEDERATED_RESULT_SCHEMA,
        "result_id": "",
        "provider_id": provider_id,
        "provider_label": provider["label"],
        "provider_record_id": _text(provider_record_id, 500),
        "title": _text(fields.get("title"), 1000) or "Untitled external record",
        "authors": _authors(fields.get("authors")),
        "published_date": _text(fields.get("published_date"), 80),
        "published_year": _year(fields.get("published_year") or fields.get("published_date")),
        "record_type": _text(fields.get("record_type"), 120) or "unknown",
        "abstract": _text(fields.get("abstract"), 8000),
        "landing_url": _url(fields.get("landing_url"), 2000),
        "identifiers": fields.get("identifiers") if isinstance(fields.get("identifiers"), dict) else {},
        "access": fields.get("access") if isinstance(fields.get("access"), dict) else {"state": "unknown"},
        "provider_records": [{"provider_id": provider_id, "provider_record_id": _text(provider_record_id, 500)}],
        "providers": [provider_id],
        "retrieved_utc": utc_now(),
        "governance": {
            "external_discovery_only": True,
            "not_sustainable_catalyst_editorial": True,
            "not_verified_evidence": True,
            "provider_identity_preserved": True,
            "explicit_save_required": True,
        },
    }
    row["canonical_key"] = _canonical_key(row)
    row["result_id"] = "federated-result-" + hashlib.sha256((provider_id + "|" + row["provider_record_id"] + "|" + row["canonical_key"]).encode("utf-8")).hexdigest()[:32]
    row["fingerprint"] = fingerprint({k: v for k, v in row.items() if k not in {"fingerprint", "retrieved_utc"}})
    return row


def _openalex_abstract(value: Any) -> str:
    if not isinstance(value, dict):
        return _text(value, 8000)
    positions: list[tuple[int, str]] = []
    for token, indexes in value.items():
        if not isinstance(indexes, list):
            continue
        for index in indexes:
            try:
                positions.append((int(index), str(token)))
            except (TypeError, ValueError):
                continue
    positions.sort(key=lambda item: item[0])
    return _text(" ".join(token for _, token in positions), 8000)


def normalize_openalex(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list(payload.get("results") or []):
        if not isinstance(item, dict):
            continue
        doi = _doi(item.get("doi"))
        oa = item.get("open_access") if isinstance(item.get("open_access"), dict) else {}
        ids = item.get("ids") if isinstance(item.get("ids"), dict) else {}
        rows.append(_result(
            "openalex", item.get("id") or ids.get("openalex") or doi,
            title=item.get("display_name") or item.get("title"),
            authors=[(x.get("author") or {}).get("display_name") for x in list(item.get("authorships") or []) if isinstance(x, dict)],
            published_date=item.get("publication_date"),
            published_year=item.get("publication_year"),
            record_type=item.get("type_crossref") or item.get("type"),
            abstract=_openalex_abstract(item.get("abstract_inverted_index") or item.get("abstract") or ""),
            landing_url=(item.get("primary_location") or {}).get("landing_page_url") if isinstance(item.get("primary_location"), dict) else (doi and f"https://doi.org/{doi}"),
            identifiers={"doi": doi, "openalex": _text(item.get("id"), 500)},
            access={"state": "open" if oa.get("is_oa") else "unknown", "is_open_access": bool(oa.get("is_oa")), "oa_status": _text(oa.get("oa_status"), 80)},
        ))
    return rows


def normalize_crossref(payload: dict[str, Any]) -> list[dict[str, Any]]:
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    rows: list[dict[str, Any]] = []
    for item in list(message.get("items") or []):
        if not isinstance(item, dict):
            continue
        doi = _doi(item.get("DOI"))
        date_parts = ((item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts") or [[]])
        year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
        authors = []
        for author in list(item.get("author") or []):
            if isinstance(author, dict):
                authors.append(" ".join(x for x in [_text(author.get("given"), 120), _text(author.get("family"), 180)] if x))
        links = list(item.get("link") or [])
        is_open = any(isinstance(link, dict) and "text/html" in str(link.get("content-type") or "") for link in links)
        rows.append(_result(
            "crossref", doi or item.get("URL") or item.get("resource", {}).get("primary", {}).get("URL", ""),
            title=item.get("title"), authors=authors, published_year=year,
            record_type=item.get("type"), abstract=item.get("abstract"),
            landing_url=item.get("URL") or (doi and f"https://doi.org/{doi}"),
            identifiers={"doi": doi, "issn": list(item.get("ISSN") or []), "isbn": [_isbn(x) for x in list(item.get("ISBN") or []) if _isbn(x)]},
            access={"state": "open-or-linked" if is_open else "unknown", "license": [x.get("URL") for x in list(item.get("license") or []) if isinstance(x, dict)][:5]},
        ))
    return rows


def normalize_europe_pmc(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result_list = payload.get("resultList") if isinstance(payload.get("resultList"), dict) else {}
    rows: list[dict[str, Any]] = []
    for item in list(result_list.get("result") or []):
        if not isinstance(item, dict):
            continue
        doi = _doi(item.get("doi"))
        pmcid = _text(item.get("pmcid"), 120)
        source = _text(item.get("source"), 40)
        ext_id = _text(item.get("id") or item.get("pmid"), 120)
        landing = f"https://europepmc.org/article/{source.lower()}/{quote(ext_id)}" if source and ext_id else (doi and f"https://doi.org/{doi}")
        rows.append(_result(
            "europe-pmc", pmcid or ext_id or doi,
            title=item.get("title"), authors=item.get("authorList", {}).get("author") if isinstance(item.get("authorList"), dict) else item.get("authorString"),
            published_date=item.get("firstPublicationDate") or item.get("journalInfo", {}).get("printPublicationDate") if isinstance(item.get("journalInfo"), dict) else item.get("firstPublicationDate"),
            published_year=item.get("pubYear"), record_type=item.get("pubType") or "article",
            abstract=item.get("abstractText"), landing_url=landing,
            identifiers={"doi": doi, "pmcid": pmcid, "pmid": _text(item.get("pmid"), 120)},
            access={"state": "open" if item.get("isOpenAccess") in {"Y", "y", True, 1} else "unknown", "is_open_access": item.get("isOpenAccess") in {"Y", "y", True, 1}, "in_epmc": item.get("inEPMC")},
        ))
    return rows


def normalize_open_library(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list(payload.get("docs") or []):
        if not isinstance(item, dict):
            continue
        key = _text(item.get("key"), 300)
        isbns = []
        for raw in list(item.get("isbn") or [])[:20]:
            value = _isbn(raw)
            if value and value not in isbns:
                isbns.append(value)
        rows.append(_result(
            "open-library", key or (isbns[0] if isbns else item.get("title")),
            title=item.get("title"), authors=item.get("author_name"), published_year=item.get("first_publish_year"),
            record_type="book", abstract="",
            landing_url=("https://openlibrary.org" + key) if key.startswith("/") else "",
            identifiers={"isbn": isbns, "openlibrary": key},
            access={"state": "catalog-record", "ebook_access": _text(item.get("ebook_access"), 80)},
        ))
    return rows


def normalize_arxiv(atom_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not atom_text.strip():
        return rows
    root = ET.fromstring(atom_text)
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    for entry in root.findall("a:entry", ns):
        entry_id = _text(entry.findtext("a:id", default="", namespaces=ns), 1000)
        arxiv_id = entry_id.rstrip("/").rsplit("/", 1)[-1]
        doi = _doi(entry.findtext("arxiv:doi", default="", namespaces=ns))
        authors = [_text(node.findtext("a:name", default="", namespaces=ns), 300) for node in entry.findall("a:author", ns)]
        landing = entry_id
        rows.append(_result(
            "arxiv", arxiv_id,
            title=entry.findtext("a:title", default="", namespaces=ns), authors=authors,
            published_date=entry.findtext("a:published", default="", namespaces=ns), record_type="preprint",
            abstract=entry.findtext("a:summary", default="", namespaces=ns), landing_url=landing,
            identifiers={"arxiv": arxiv_id, "doi": doi}, access={"state": "open", "is_open_access": True},
        ))
    return rows


def provider_catalog() -> dict[str, Any]:
    return {
        "schema": FEDERATED_PROVIDER_CATALOG_SCHEMA,
        "providers": [{"provider_id": key, **value} for key, value in PROVIDERS.items()],
        "governance": {
            "fixed_provider_allowlist": True,
            "arbitrary_remote_urls_forbidden": True,
            "external_discovery_is_not_editorial": True,
            "external_discovery_is_not_verified_evidence": True,
            "explicit_library_save_required": True,
        },
    }


def provider_request(provider_id: str, query: str, limit: int, *, openalex_api_key: str = "", contact_email: str = "") -> tuple[str, dict[str, Any]]:
    provider = PROVIDERS[provider_id]
    base = provider["base_url"] + provider["search_path"]
    limit = max(1, min(50, int(limit)))
    query = _text(query, 3000)
    if provider_id == "openalex":
        params: dict[str, Any] = {"search": query, "per-page": limit}
        if openalex_api_key:
            params["api_key"] = openalex_api_key
        return base, params
    if provider_id == "crossref":
        params = {"query.bibliographic": query, "rows": limit}
        if contact_email:
            params["mailto"] = contact_email
        return base, params
    if provider_id == "europe-pmc":
        return base, {"query": query, "format": "json", "pageSize": limit, "resultType": "core"}
    if provider_id == "open-library":
        return base, {"q": query, "limit": limit}
    if provider_id == "arxiv":
        return base, {"search_query": f"all:{query}", "start": 0, "max_results": limit, "sortBy": "relevance", "sortOrder": "descending"}
    raise ValueError(f"Unsupported federated provider: {provider_id}")


def normalize_provider_response(provider_id: str, response: httpx.Response) -> list[dict[str, Any]]:
    if provider_id == "arxiv":
        return normalize_arxiv(response.text)
    payload = response.json()
    if provider_id == "openalex":
        return normalize_openalex(payload)
    if provider_id == "crossref":
        return normalize_crossref(payload)
    if provider_id == "europe-pmc":
        return normalize_europe_pmc(payload)
    if provider_id == "open-library":
        return normalize_open_library(payload)
    return []


def deduplicate_results(results: list[dict[str, Any]], limit: int = 100) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in results:
        key = str(row.get("canonical_key") or _canonical_key(row))
        if key not in merged:
            merged[key] = dict(row)
            order.append(key)
            continue
        current = merged[key]
        for provider_id in list(row.get("providers") or []):
            if provider_id not in current.setdefault("providers", []):
                current["providers"].append(provider_id)
        known = {(x.get("provider_id"), x.get("provider_record_id")) for x in current.setdefault("provider_records", []) if isinstance(x, dict)}
        for record in list(row.get("provider_records") or []):
            if isinstance(record, dict) and (record.get("provider_id"), record.get("provider_record_id")) not in known:
                current["provider_records"].append(record)
        for field in ["abstract", "landing_url", "published_date", "published_year", "record_type"]:
            if not current.get(field) and row.get(field):
                current[field] = row[field]
        current["fingerprint"] = fingerprint({k: v for k, v in current.items() if k not in {"fingerprint", "retrieved_utc"}})
    return [merged[key] for key in order[: max(1, min(500, int(limit)))]]


async def search_provider(
    provider_id: str,
    query: str,
    limit: int,
    *,
    timeout_seconds: float = 12.0,
    openalex_api_key: str = "",
    contact_email: str = "",
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unsupported federated provider: {provider_id}")
    url, params = provider_request(provider_id, query, limit, openalex_api_key=openalex_api_key, contact_email=contact_email)
    owned = client is None
    active = client or httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True, headers={"Accept": "application/json, application/atom+xml;q=0.9", "User-Agent": "Sustainable-Catalyst-Research-Librarian/8.0.0"})
    try:
        response = await active.get(url, params=params)
        response.raise_for_status()
        rows = normalize_provider_response(provider_id, response)
        return {"provider_id": provider_id, "ok": True, "count": len(rows), "results": rows, "error": ""}
    except (httpx.HTTPError, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
        return {"provider_id": provider_id, "ok": False, "count": 0, "results": [], "error": _text(str(exc), 1000)}
    finally:
        if owned:
            await active.aclose()


async def run_federated_search(
    *,
    query: str,
    provider_ids: list[str] | None = None,
    limit_per_provider: int = 10,
    result_limit: int = 50,
    timeout_seconds: float = 12.0,
    openalex_api_key: str = "",
    contact_email: str = "",
) -> dict[str, Any]:
    selected: list[str] = []
    for provider_id in provider_ids or list(PROVIDERS):
        clean = str(provider_id or "").strip().lower()
        if clean in PROVIDERS and clean not in selected:
            selected.append(clean)
    if not selected:
        raise ValueError("Federated discovery requires at least one supported provider.")
    import asyncio
    outcomes = await asyncio.gather(*[
        search_provider(provider_id, query, limit_per_provider, timeout_seconds=timeout_seconds, openalex_api_key=openalex_api_key, contact_email=contact_email)
        for provider_id in selected
    ])
    raw = [row for outcome in outcomes for row in outcome.get("results", [])]
    results = deduplicate_results(raw, result_limit)
    ok_count = sum(1 for outcome in outcomes if outcome.get("ok"))
    status = "complete" if ok_count == len(outcomes) else ("partial" if ok_count else "failed")
    return {
        "schema": FEDERATED_SEARCH_SCHEMA,
        "search_id": _id("federated-search"),
        "query": _text(query, 3000),
        "providers": selected,
        "provider_outcomes": [{
            "provider_id": outcome.get("provider_id"),
            "ok": bool(outcome.get("ok")),
            "count": int(outcome.get("count") or 0),
            "error": _text(outcome.get("error"), 1000),
        } for outcome in outcomes],
        "status": status,
        "result_count": len(results),
        "results": results,
        "created_utc": utc_now(),
        "governance": {
            "external_discovery_only": True,
            "not_sustainable_catalyst_editorial": True,
            "not_verified_evidence": True,
            "provider_failures_are_visible": True,
            "deduplication_does_not_merge_provider_identity": True,
            "explicit_library_save_required": True,
        },
    }


def normalize_search_record(payload: dict[str, Any], *, owner_ref: str, project_id: str = "", context_id: str = "") -> dict[str, Any]:
    clean = {
        **payload,
        "owner_ref": _text(owner_ref, 220),
        "project_id": _text(project_id, 220),
        "context_id": _text(context_id, 220),
    }
    clean["fingerprint"] = fingerprint({k: v for k, v in clean.items() if k != "fingerprint"})
    return clean


def search_summary(searches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": FEDERATED_SEARCH_SUMMARY_SCHEMA,
        "search_count": len(searches),
        "result_count": sum(int(x.get("result_count") or 0) for x in searches),
        "providers": sorted({provider for x in searches for provider in list(x.get("providers") or [])}),
        "partial_searches": sum(1 for x in searches if str(x.get("status") or "") == "partial"),
        "failed_searches": sum(1 for x in searches if str(x.get("status") or "") == "failed"),
    }


def result_to_library_payload(result: dict[str, Any], *, owner_ref: str, project_id: str = "", tags: list[str] | None = None) -> dict[str, Any]:
    if str((result.get("governance") or {}).get("external_discovery_only", "")).lower() not in {"true", "1"} and (result.get("governance") or {}).get("external_discovery_only") is not True:
        raise ValueError("Only a normalized federated-discovery result can be saved through this import contract.")
    provider_records = [x for x in list(result.get("provider_records") or []) if isinstance(x, dict)]
    provider_label = ", ".join([PROVIDERS[x].get("label", x) for x in list(result.get("providers") or []) if x in PROVIDERS])
    project_ids = [project_id] if project_id else []
    return {
        "object_type": "source",
        "title": _text(result.get("title"), 500),
        "description": _text(result.get("abstract"), 8000),
        "owner_ref": _text(owner_ref, 220),
        "source_scope": "external-reference",
        "visibility": "private",
        "status": "saved",
        "tags": list(tags or [])[:50],
        "relationships": {"project_ids": project_ids, "room_ids": [], "bundle_ids": [], "parent_object_ids": []},
        "provenance": {
            "origin_system": "federated-research",
            "origin_object_id": _text(result.get("result_id"), 220),
            "source_record_id": _text(result.get("provider_record_id"), 220),
            "canonical_url": _url(result.get("landing_url"), 1600),
            "provider": provider_label,
            "captured_utc": utc_now(),
        },
        "payload": {
            "federated_result_schema": FEDERATED_RESULT_SCHEMA,
            "canonical_key": _text(result.get("canonical_key"), 500),
            "providers": list(result.get("providers") or [])[:20],
            "provider_records": provider_records[:50],
            "identifiers": result.get("identifiers") if isinstance(result.get("identifiers"), dict) else {},
            "published_date": _text(result.get("published_date"), 80),
            "published_year": _text(result.get("published_year"), 20),
            "record_type": _text(result.get("record_type"), 120),
            "access": result.get("access") if isinstance(result.get("access"), dict) else {},
            "federated_result_fingerprint": _text(result.get("fingerprint"), 128),
            "governance": {
                "external_reference_only": True,
                "not_editorial_approval": True,
                "not_truth_judgment": True,
                "provider_identity_preserved": True,
            },
        },
    }
