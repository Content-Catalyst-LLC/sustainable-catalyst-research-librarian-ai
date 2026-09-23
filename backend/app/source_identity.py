from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import settings
from .database_identity import validate_schema_name
from .models import utc_now

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]

SOURCE_IDENTITY_SCHEMA = "sc-research-librarian-source-identity/1.0"
SOURCE_INSTANCE_SCHEMA = "sc-research-librarian-source-instance/1.0"
CITATION_GRAPH_SCHEMA = "sc-research-librarian-citation-graph/1.0"
IDENTITY_PRIORITY = ("doi", "arxiv", "pmid", "isbn", "url")

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", re.I)
_ARXIV_PREFIX = re.compile(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv\s*:\s*)", re.I)
_PMID_PREFIX = re.compile(r"^(?:https?://pubmed\.ncbi\.nlm\.nih\.gov/|pmid\s*:\s*)", re.I)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_title(value: str) -> str:
    text = _clean(value).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_person(value: str) -> str:
    text = _clean(value).casefold()
    text = re.sub(r"[^\w\s'-]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value: str) -> str:
    raw = _clean(value)
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        scheme = (parts.scheme or "https").lower()
        host = (parts.hostname or "").lower()
        if not host:
            return raw
        port = parts.port
        netloc = host if not port or (scheme == "https" and port == 443) or (scheme == "http" and port == 80) else f"{host}:{port}"
        path = re.sub(r"/{2,}", "/", parts.path or "/")
        if path != "/":
            path = path.rstrip("/")
        query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")))
        return urlunsplit((scheme, netloc, path, query, ""))
    except Exception:
        return raw


def normalize_identifier(kind: str, value: Any) -> str:
    kind = _clean(kind).lower()
    raw = _clean(value)
    if not raw:
        return ""
    if kind == "doi":
        return _DOI_PREFIX.sub("", raw).strip().rstrip(".,;)").lower()
    if kind == "arxiv":
        out = _ARXIV_PREFIX.sub("", raw).strip().lower().removesuffix(".pdf")
        return re.sub(r"v\d+$", "", out)
    if kind == "pmid":
        return _PMID_PREFIX.sub("", raw).strip().strip("/")
    if kind == "isbn":
        return re.sub(r"[^0-9Xx]", "", raw).upper()
    if kind == "url":
        return normalize_url(raw)
    return raw.casefold()


def normalize_identifiers(values: dict[str, Any] | None, source_url: str = "") -> dict[str, list[str]]:
    values = values or {}
    out: dict[str, list[str]] = {kind: [] for kind in IDENTITY_PRIORITY}
    for kind in IDENTITY_PRIORITY:
        raw_values = values.get(kind, values.get("urls" if kind == "url" else kind, []))
        if isinstance(raw_values, str):
            raw_values = [raw_values]
        if not isinstance(raw_values, list):
            continue
        for value in raw_values:
            normalized = normalize_identifier(kind, value)
            if normalized and normalized not in out[kind]:
                out[kind].append(normalized)
    if source_url:
        normalized = normalize_identifier("url", source_url)
        if normalized and normalized not in out["url"]:
            out["url"].insert(0, normalized)
    return out


def identity_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    document = dict(payload.get("parsed_document") or {})
    title = _clean(payload.get("title") or document.get("title"))
    authors = payload.get("authors") or document.get("authors") or []
    if not isinstance(authors, list):
        authors = [authors]
    institutions = payload.get("institutions") or []
    if not isinstance(institutions, list):
        institutions = [institutions]
    explicit_identifiers = dict(payload.get("identifiers") or {})
    document_identifiers = dict(document.get("identifiers") or {})
    if explicit_identifiers:
        identity_identifiers = explicit_identifiers
    else:
        # v8.5 document parsing intentionally extracts identifiers from the entire
        # document, including the bibliography. Those cited-work identifiers must
        # never identify the citing work. Remove identifiers observed in parsed
        # references before canonical source resolution.
        cited: dict[str, set[str]] = {kind: set() for kind in IDENTITY_PRIORITY}
        for reference in document.get("references") or []:
            normalized_ref = normalize_identifiers(dict(reference.get("identifiers") or {}))
            for kind, values in normalized_ref.items():
                cited.setdefault(kind, set()).update(values)
        identity_identifiers = {}
        normalized_document = normalize_identifiers(document_identifiers)
        for kind, values in normalized_document.items():
            identity_identifiers[kind] = [value for value in values if value not in cited.get(kind, set())]
    identifiers = normalize_identifiers(
        identity_identifiers,
        _clean(payload.get("source_url") or document.get("source_url")),
    )
    year = payload.get("publication_year")
    try:
        year = int(year) if year else None
    except (TypeError, ValueError):
        year = None
    normalized_title = normalize_title(title)
    author_keys = [normalize_person(x) for x in authors if normalize_person(str(x))]
    fallback_key = ""
    if normalized_title:
        fallback_key = _hash("\n".join([normalized_title, str(year or ""), author_keys[0] if author_keys else ""]))
    return {
        "schema": SOURCE_IDENTITY_SCHEMA,
        "title": title[:1000],
        "normalized_title": normalized_title[:1000],
        "authors": [_clean(x)[:500] for x in authors if _clean(x)][:200],
        "author_keys": author_keys[:200],
        "institutions": [_clean(x)[:500] for x in institutions if _clean(x)][:200],
        "publication_year": year,
        "identifiers": identifiers,
        "source_url": normalize_url(_clean(payload.get("source_url") or document.get("source_url"))),
        "filename": _clean(payload.get("filename") or document.get("filename"))[:1000],
        "media_type": _clean(payload.get("media_type") or document.get("media_type"))[:300],
        "content_fingerprint": _clean(payload.get("content_fingerprint") or document.get("fingerprint"))[:256],
        "version_label": _clean(payload.get("version_label"))[:300],
        "fallback_key": fallback_key,
        "references": list(payload.get("references") or document.get("references") or [])[:2000],
        "metadata": dict(payload.get("metadata") or {}),
    }


class SourceIdentityConflict(ValueError):
    pass


class SourceGraphStore:
    """Canonical scholarly identity + citation graph. Postgres is authoritative in production."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "source_graph.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres source graph requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.sqlite_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _postgres(self, *, migration: bool = False) -> Iterator[Any]:
        url = (settings.direct_database_url if migration else settings.database_url) or settings.database_url
        connection = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        try:
            connection.execute(f'SET search_path TO "{self.database_schema}"')
            yield connection
        finally:
            connection.close()

    def _migrate_sqlite(self) -> None:
        with self._lock, self._sqlite() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS canonical_sources (
                canonical_source_id TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'resolved',
                title TEXT NOT NULL DEFAULT '',
                normalized_title TEXT NOT NULL DEFAULT '',
                publication_year INTEGER,
                fallback_key TEXT NOT NULL DEFAULT '',
                fingerprint TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_utc TEXT NOT NULL,
                updated_utc TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_canonical_sources_fallback ON canonical_sources(fallback_key) WHERE fallback_key <> '';
            CREATE TABLE IF NOT EXISTS source_identifiers (
                identifier_type TEXT NOT NULL,
                identifier_value TEXT NOT NULL,
                canonical_source_id TEXT NOT NULL REFERENCES canonical_sources(canonical_source_id) ON DELETE CASCADE,
                created_utc TEXT NOT NULL,
                PRIMARY KEY(identifier_type, identifier_value)
            );
            CREATE INDEX IF NOT EXISTS idx_source_identifiers_source ON source_identifiers(canonical_source_id);
            CREATE TABLE IF NOT EXISTS source_instances (
                instance_id TEXT PRIMARY KEY,
                canonical_source_id TEXT NOT NULL REFERENCES canonical_sources(canonical_source_id) ON DELETE CASCADE,
                source_url TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL DEFAULT '',
                media_type TEXT NOT NULL DEFAULT '',
                content_fingerprint TEXT NOT NULL DEFAULT '',
                version_label TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_utc TEXT NOT NULL,
                updated_utc TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_source_instance_unique_url ON source_instances(canonical_source_id,source_url) WHERE source_url <> '';
            CREATE UNIQUE INDEX IF NOT EXISTS idx_source_instance_unique_hash ON source_instances(canonical_source_id,content_fingerprint) WHERE content_fingerprint <> '';
            CREATE TABLE IF NOT EXISTS source_authors (
                canonical_source_id TEXT NOT NULL REFERENCES canonical_sources(canonical_source_id) ON DELETE CASCADE,
                author_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY(canonical_source_id,author_id)
            );
            CREATE TABLE IF NOT EXISTS source_institutions (
                canonical_source_id TEXT NOT NULL REFERENCES canonical_sources(canonical_source_id) ON DELETE CASCADE,
                institution_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                PRIMARY KEY(canonical_source_id,institution_id)
            );
            CREATE TABLE IF NOT EXISTS citation_edges (
                edge_id TEXT PRIMARY KEY,
                citing_source_id TEXT NOT NULL REFERENCES canonical_sources(canonical_source_id) ON DELETE CASCADE,
                cited_source_id TEXT NOT NULL REFERENCES canonical_sources(canonical_source_id) ON DELETE CASCADE,
                raw_reference TEXT NOT NULL DEFAULT '',
                reference_index INTEGER,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_utc TEXT NOT NULL,
                UNIQUE(citing_source_id,cited_source_id,reference_index)
            );
            CREATE INDEX IF NOT EXISTS idx_citation_out ON citation_edges(citing_source_id);
            CREATE INDEX IF NOT EXISTS idx_citation_in ON citation_edges(cited_source_id);
            CREATE TABLE IF NOT EXISTS source_resolution_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_source_id TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_utc TEXT NOT NULL
            );
            """)

    def _migrate_postgres(self) -> None:
        with self._postgres(migration=True) as c:
            c.execute("SELECT pg_advisory_lock(hashtext('sc_rl_source_graph_migration'))")
            c.commit()
            try:
                for sql in (
                    """CREATE TABLE IF NOT EXISTS sc_rl_canonical_sources (canonical_source_id TEXT PRIMARY KEY,state TEXT NOT NULL DEFAULT 'resolved',title TEXT NOT NULL DEFAULT '',normalized_title TEXT NOT NULL DEFAULT '',publication_year INTEGER,fallback_key TEXT NOT NULL DEFAULT '',fingerprint TEXT NOT NULL,metadata JSONB NOT NULL DEFAULT '{}'::jsonb,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
                    """CREATE INDEX IF NOT EXISTS idx_sc_rl_canonical_sources_fallback ON sc_rl_canonical_sources(fallback_key) WHERE fallback_key <> ''""",
                    """CREATE TABLE IF NOT EXISTS sc_rl_source_identifiers (identifier_type TEXT NOT NULL,identifier_value TEXT NOT NULL,canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),PRIMARY KEY(identifier_type,identifier_value))""",
                    """CREATE INDEX IF NOT EXISTS idx_sc_rl_source_identifiers_source ON sc_rl_source_identifiers(canonical_source_id)""",
                    """CREATE TABLE IF NOT EXISTS sc_rl_source_instances (instance_id TEXT PRIMARY KEY,canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,source_url TEXT NOT NULL DEFAULT '',filename TEXT NOT NULL DEFAULT '',media_type TEXT NOT NULL DEFAULT '',content_fingerprint TEXT NOT NULL DEFAULT '',version_label TEXT NOT NULL DEFAULT '',metadata JSONB NOT NULL DEFAULT '{}'::jsonb,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
                    """CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_source_instance_unique_url ON sc_rl_source_instances(canonical_source_id,source_url) WHERE source_url <> ''""",
                    """CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_source_instance_unique_hash ON sc_rl_source_instances(canonical_source_id,content_fingerprint) WHERE content_fingerprint <> ''""",
                    """CREATE TABLE IF NOT EXISTS sc_rl_source_authors (canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,author_id TEXT NOT NULL,display_name TEXT NOT NULL,normalized_name TEXT NOT NULL,position INTEGER NOT NULL,PRIMARY KEY(canonical_source_id,author_id))""",
                    """CREATE TABLE IF NOT EXISTS sc_rl_source_institutions (canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,institution_id TEXT NOT NULL,display_name TEXT NOT NULL,normalized_name TEXT NOT NULL,PRIMARY KEY(canonical_source_id,institution_id))""",
                    """CREATE TABLE IF NOT EXISTS sc_rl_citation_edges (edge_id TEXT PRIMARY KEY,citing_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,cited_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,raw_reference TEXT NOT NULL DEFAULT '',reference_index INTEGER,confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(citing_source_id,cited_source_id,reference_index))""",
                    """CREATE INDEX IF NOT EXISTS idx_sc_rl_citation_out ON sc_rl_citation_edges(citing_source_id)""",
                    """CREATE INDEX IF NOT EXISTS idx_sc_rl_citation_in ON sc_rl_citation_edges(cited_source_id)""",
                    """CREATE TABLE IF NOT EXISTS sc_rl_source_resolution_events (event_id BIGSERIAL PRIMARY KEY,canonical_source_id TEXT NOT NULL,action TEXT NOT NULL,payload JSONB NOT NULL DEFAULT '{}'::jsonb,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
                ):
                    c.execute(sql)
                c.commit()
            except Exception:
                c.rollback(); raise
            finally:
                try:
                    c.execute("SELECT pg_advisory_unlock(hashtext('sc_rl_source_graph_migration'))"); c.commit()
                except Exception:
                    c.rollback()

    @staticmethod
    def _row_dict(row: Any) -> dict[str, Any]:
        if row is None:
            return {}
        out = dict(row)
        for key, value in list(out.items()):
            if isinstance(value, datetime):
                out[key] = value.astimezone(timezone.utc).isoformat()
        for key in ("metadata", "metadata_json"):
            if key in out:
                value = out.pop(key)
                if isinstance(value, str):
                    try: value = json.loads(value)
                    except json.JSONDecodeError: value = {}
                out["metadata"] = value or {}
        return out

    def runtime(self) -> dict[str, Any]:
        return {"schema": SOURCE_IDENTITY_SCHEMA, "storage_backend": self.backend, "durable": True, "canonical_identity": True, "citation_graph": True}

    def _lookup_ids_sqlite(self, c: sqlite3.Connection, ids: dict[str, list[str]]) -> set[str]:
        matches: set[str] = set()
        for kind in IDENTITY_PRIORITY:
            for value in ids.get(kind, []):
                row = c.execute("SELECT canonical_source_id FROM source_identifiers WHERE identifier_type=? AND identifier_value=?", (kind, value)).fetchone()
                if row: matches.add(str(row[0]))
        return matches

    def _lookup_ids_postgres(self, c: Any, ids: dict[str, list[str]]) -> set[str]:
        matches: set[str] = set()
        for kind in IDENTITY_PRIORITY:
            for value in ids.get(kind, []):
                row = c.execute("SELECT canonical_source_id FROM sc_rl_source_identifiers WHERE identifier_type=%s AND identifier_value=%s", (kind, value)).fetchone()
                if row: matches.add(str(row["canonical_source_id"]))
        return matches

    def resolve(self, payload: dict[str, Any], *, register_citations: bool = True) -> dict[str, Any]:
        candidate = identity_candidate(payload)
        if not candidate["title"] and not any(candidate["identifiers"].values()):
            raise ValueError("A source requires a title or a stable identifier.")
        return self._resolve_postgres(candidate, register_citations) if self.backend == "postgres" else self._resolve_sqlite(candidate, register_citations)

    def _canonical_seed(self, candidate: dict[str, Any]) -> str:
        for kind in IDENTITY_PRIORITY:
            values = candidate["identifiers"].get(kind, [])
            if values:
                return f"{kind}:{values[0]}"
        if candidate.get("fallback_key"):
            return "fallback:" + candidate["fallback_key"]
        return "content:" + (candidate.get("content_fingerprint") or _hash(candidate.get("title") or "untitled"))

    def _resolve_sqlite(self, candidate: dict[str, Any], register_citations: bool) -> dict[str, Any]:
        now = utc_now()
        with self._lock, self._sqlite() as c:
            c.execute("BEGIN IMMEDIATE")
            matches = self._lookup_ids_sqlite(c, candidate["identifiers"])
            if len(matches) > 1:
                c.rollback(); raise SourceIdentityConflict(f"Stable identifiers map to multiple canonical sources: {sorted(matches)}")
            source_id = next(iter(matches), "")
            resolution = "stable-identifier" if source_id else ""
            if not source_id and candidate["fallback_key"]:
                rows = c.execute("SELECT canonical_source_id FROM canonical_sources WHERE fallback_key=? ORDER BY created_utc LIMIT 2", (candidate["fallback_key"],)).fetchall()
                if len(rows) == 1:
                    source_id = str(rows[0][0]); resolution = "bibliographic-fingerprint"
            created = False
            if not source_id:
                source_id = "source:" + _hash(self._canonical_seed(candidate))[:32]
                fingerprint = _hash(_json(candidate))
                c.execute("INSERT OR IGNORE INTO canonical_sources(canonical_source_id,state,title,normalized_title,publication_year,fallback_key,fingerprint,metadata_json,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?,?)", (source_id,"resolved" if candidate["title"] else "stub",candidate["title"],candidate["normalized_title"],candidate["publication_year"],candidate["fallback_key"],fingerprint,_json(candidate["metadata"]),now,now))
                created = True; resolution = "created"
            self._upsert_components_sqlite(c, source_id, candidate, now)
            c.execute("INSERT INTO source_resolution_events(canonical_source_id,action,payload_json,created_utc) VALUES(?,?,?,?)", (source_id,resolution,_json({"identifiers":candidate["identifiers"],"title":candidate["title"]}),now))
            c.commit()
        citations = self.register_references(source_id, candidate["references"]) if register_citations and candidate["references"] else {"created":0,"existing":0,"unresolved":0}
        return {"schema":SOURCE_IDENTITY_SCHEMA,"canonical_source_id":source_id,"created":created,"resolution":resolution,"source":self.get(source_id),"citations":citations}

    def _upsert_components_sqlite(self, c: sqlite3.Connection, source_id: str, candidate: dict[str, Any], now: str) -> None:
        current = c.execute("SELECT * FROM canonical_sources WHERE canonical_source_id=?", (source_id,)).fetchone()
        if current:
            title = candidate["title"] or str(current["title"])
            norm = candidate["normalized_title"] or str(current["normalized_title"])
            year = candidate["publication_year"] or current["publication_year"]
            fallback = candidate["fallback_key"] or str(current["fallback_key"])
            state = "resolved" if title else str(current["state"])
            metadata = json.loads(str(current["metadata_json"] or "{}")); metadata.update(candidate["metadata"])
            fingerprint = _hash(_json({"title":title,"year":year,"ids":candidate["identifiers"],"authors":candidate["authors"]}))
            c.execute("UPDATE canonical_sources SET state=?,title=?,normalized_title=?,publication_year=?,fallback_key=?,fingerprint=?,metadata_json=?,updated_utc=? WHERE canonical_source_id=?", (state,title,norm,year,fallback,fingerprint,_json(metadata),now,source_id))
        for kind, values in candidate["identifiers"].items():
            for value in values:
                try: c.execute("INSERT INTO source_identifiers(identifier_type,identifier_value,canonical_source_id,created_utc) VALUES(?,?,?,?)", (kind,value,source_id,now))
                except sqlite3.IntegrityError:
                    row=c.execute("SELECT canonical_source_id FROM source_identifiers WHERE identifier_type=? AND identifier_value=?",(kind,value)).fetchone()
                    if row and str(row[0]) != source_id: raise SourceIdentityConflict(f"{kind}:{value} already belongs to {row[0]}")
        self._upsert_instance_sqlite(c, source_id, candidate, now)
        for position, name in enumerate(candidate["authors"]):
            normalized=normalize_person(name); author_id="author:"+_hash(normalized)[:24]
            c.execute("INSERT OR REPLACE INTO source_authors(canonical_source_id,author_id,display_name,normalized_name,position) VALUES(?,?,?,?,?)",(source_id,author_id,name,normalized,position))
        for name in candidate["institutions"]:
            normalized=normalize_person(name); institution_id="institution:"+_hash(normalized)[:24]
            c.execute("INSERT OR REPLACE INTO source_institutions(canonical_source_id,institution_id,display_name,normalized_name) VALUES(?,?,?,?)",(source_id,institution_id,name,normalized))

    def _upsert_instance_sqlite(self, c: sqlite3.Connection, source_id: str, candidate: dict[str, Any], now: str) -> None:
        if not any((candidate["source_url"],candidate["filename"],candidate["content_fingerprint"])): return
        seed="\n".join([source_id,candidate["source_url"],candidate["content_fingerprint"],candidate["filename"],candidate["version_label"]])
        instance_id="instance:"+_hash(seed)[:32]
        c.execute("INSERT OR IGNORE INTO source_instances(instance_id,canonical_source_id,source_url,filename,media_type,content_fingerprint,version_label,metadata_json,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?,?)",(instance_id,source_id,candidate["source_url"],candidate["filename"],candidate["media_type"],candidate["content_fingerprint"],candidate["version_label"],_json(candidate["metadata"]),now,now))

    def _resolve_postgres(self, candidate: dict[str, Any], register_citations: bool) -> dict[str, Any]:
        now = utc_now()
        with self._postgres() as c:
            matches = self._lookup_ids_postgres(c, candidate["identifiers"])
            if len(matches)>1: c.rollback(); raise SourceIdentityConflict(f"Stable identifiers map to multiple canonical sources: {sorted(matches)}")
            source_id=next(iter(matches),""); resolution="stable-identifier" if source_id else ""
            if not source_id and candidate["fallback_key"]:
                rows=c.execute("SELECT canonical_source_id FROM sc_rl_canonical_sources WHERE fallback_key=%s ORDER BY created_utc LIMIT 2",(candidate["fallback_key"],)).fetchall()
                if len(rows)==1: source_id=str(rows[0]["canonical_source_id"]); resolution="bibliographic-fingerprint"
            created=False
            if not source_id:
                source_id="source:"+_hash(self._canonical_seed(candidate))[:32]
                c.execute("INSERT INTO sc_rl_canonical_sources(canonical_source_id,state,title,normalized_title,publication_year,fallback_key,fingerprint,metadata,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(canonical_source_id) DO NOTHING",(source_id,"resolved" if candidate["title"] else "stub",candidate["title"],candidate["normalized_title"],candidate["publication_year"],candidate["fallback_key"],_hash(_json(candidate)),Jsonb(candidate["metadata"]),now,now))
                created=True; resolution="created"
            self._upsert_components_postgres(c,source_id,candidate,now)
            c.execute("INSERT INTO sc_rl_source_resolution_events(canonical_source_id,action,payload,created_utc) VALUES(%s,%s,%s,%s)",(source_id,resolution,Jsonb({"identifiers":candidate["identifiers"],"title":candidate["title"]}),now)); c.commit()
        citations=self.register_references(source_id,candidate["references"]) if register_citations and candidate["references"] else {"created":0,"existing":0,"unresolved":0}
        return {"schema":SOURCE_IDENTITY_SCHEMA,"canonical_source_id":source_id,"created":created,"resolution":resolution,"source":self.get(source_id),"citations":citations}

    def _upsert_components_postgres(self,c:Any,source_id:str,candidate:dict[str,Any],now:str)->None:
        row=c.execute("SELECT * FROM sc_rl_canonical_sources WHERE canonical_source_id=%s FOR UPDATE",(source_id,)).fetchone()
        if row:
            metadata=dict(row.get("metadata") or {}); metadata.update(candidate["metadata"])
            title=candidate["title"] or str(row.get("title") or ""); norm=candidate["normalized_title"] or str(row.get("normalized_title") or ""); year=candidate["publication_year"] or row.get("publication_year"); fallback=candidate["fallback_key"] or str(row.get("fallback_key") or "")
            fp=_hash(_json({"title":title,"year":year,"ids":candidate["identifiers"],"authors":candidate["authors"]}))
            c.execute("UPDATE sc_rl_canonical_sources SET state=%s,title=%s,normalized_title=%s,publication_year=%s,fallback_key=%s,fingerprint=%s,metadata=%s,updated_utc=%s WHERE canonical_source_id=%s",("resolved" if title else str(row.get("state") or "stub"),title,norm,year,fallback,fp,Jsonb(metadata),now,source_id))
        for kind,values in candidate["identifiers"].items():
            for value in values:
                existing=c.execute("SELECT canonical_source_id FROM sc_rl_source_identifiers WHERE identifier_type=%s AND identifier_value=%s",(kind,value)).fetchone()
                if existing and str(existing["canonical_source_id"])!=source_id: raise SourceIdentityConflict(f"{kind}:{value} already belongs to {existing['canonical_source_id']}")
                c.execute("INSERT INTO sc_rl_source_identifiers(identifier_type,identifier_value,canonical_source_id,created_utc) VALUES(%s,%s,%s,%s) ON CONFLICT(identifier_type,identifier_value) DO NOTHING",(kind,value,source_id,now))
        if any((candidate["source_url"],candidate["filename"],candidate["content_fingerprint"])):
            seed="\n".join([source_id,candidate["source_url"],candidate["content_fingerprint"],candidate["filename"],candidate["version_label"]]); instance_id="instance:"+_hash(seed)[:32]
            c.execute("INSERT INTO sc_rl_source_instances(instance_id,canonical_source_id,source_url,filename,media_type,content_fingerprint,version_label,metadata,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(instance_id) DO NOTHING",(instance_id,source_id,candidate["source_url"],candidate["filename"],candidate["media_type"],candidate["content_fingerprint"],candidate["version_label"],Jsonb(candidate["metadata"]),now,now))
        for position,name in enumerate(candidate["authors"]):
            normalized=normalize_person(name); author_id="author:"+_hash(normalized)[:24]
            c.execute("INSERT INTO sc_rl_source_authors(canonical_source_id,author_id,display_name,normalized_name,position) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(canonical_source_id,author_id) DO UPDATE SET display_name=EXCLUDED.display_name,position=EXCLUDED.position",(source_id,author_id,name,normalized,position))
        for name in candidate["institutions"]:
            normalized=normalize_person(name); institution_id="institution:"+_hash(normalized)[:24]
            c.execute("INSERT INTO sc_rl_source_institutions(canonical_source_id,institution_id,display_name,normalized_name) VALUES(%s,%s,%s,%s) ON CONFLICT(canonical_source_id,institution_id) DO UPDATE SET display_name=EXCLUDED.display_name",(source_id,institution_id,name,normalized))

    def _create_stub(self, identifiers: dict[str,list[str]], raw: str) -> str | None:
        if not any(identifiers.values()): return None
        payload={"title":"","identifiers":identifiers,"metadata":{"citation_stub":True,"raw_reference":raw[:4000]}}
        return str(self.resolve(payload,register_citations=False)["canonical_source_id"])

    def register_references(self, citing_source_id: str, references: list[dict[str,Any]]) -> dict[str,int]:
        created=existing=unresolved=0
        for position,reference in enumerate(references[:2000],start=1):
            ids=normalize_identifiers(dict(reference.get("identifiers") or {}))
            cited=self._create_stub(ids,str(reference.get("raw") or ""))
            if not cited or cited==citing_source_id:
                unresolved+=1; continue
            raw=_clean(reference.get("raw"))[:8000]; index=int(reference.get("index") or position); edge_id="citation:"+_hash(f"{citing_source_id}\n{cited}\n{index}")[:32]
            inserted=self._insert_edge(edge_id,citing_source_id,cited,raw,index)
            created += int(inserted); existing += int(not inserted)
        return {"created":created,"existing":existing,"unresolved":unresolved}

    def _insert_edge(self,edge_id:str,citing:str,cited:str,raw:str,index:int)->bool:
        now=utc_now()
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("INSERT INTO sc_rl_citation_edges(edge_id,citing_source_id,cited_source_id,raw_reference,reference_index,confidence,created_utc) VALUES(%s,%s,%s,%s,%s,1.0,%s) ON CONFLICT DO NOTHING RETURNING edge_id",(edge_id,citing,cited,raw,index,now)).fetchone(); c.commit(); return bool(row)
        with self._lock,self._sqlite() as c:
            before=c.total_changes; c.execute("INSERT OR IGNORE INTO citation_edges(edge_id,citing_source_id,cited_source_id,raw_reference,reference_index,confidence,created_utc) VALUES(?,?,?,?,?,1.0,?)",(edge_id,citing,cited,raw,index,now)); return c.total_changes>before

    def get(self,source_id:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("SELECT * FROM sc_rl_canonical_sources WHERE canonical_source_id=%s",(source_id,)).fetchone()
                if not row:return {}
                ids=c.execute("SELECT identifier_type,identifier_value FROM sc_rl_source_identifiers WHERE canonical_source_id=%s ORDER BY identifier_type,identifier_value",(source_id,)).fetchall(); instances=c.execute("SELECT * FROM sc_rl_source_instances WHERE canonical_source_id=%s ORDER BY created_utc",(source_id,)).fetchall(); authors=c.execute("SELECT author_id,display_name,normalized_name,position FROM sc_rl_source_authors WHERE canonical_source_id=%s ORDER BY position",(source_id,)).fetchall(); institutions=c.execute("SELECT institution_id,display_name,normalized_name FROM sc_rl_source_institutions WHERE canonical_source_id=%s ORDER BY display_name",(source_id,)).fetchall()
                c.commit()
                return self._assemble(row,ids,instances,authors,institutions)
        with self._sqlite() as c:
            row=c.execute("SELECT * FROM canonical_sources WHERE canonical_source_id=?",(source_id,)).fetchone()
            if not row:return {}
            ids=c.execute("SELECT identifier_type,identifier_value FROM source_identifiers WHERE canonical_source_id=? ORDER BY identifier_type,identifier_value",(source_id,)).fetchall(); instances=c.execute("SELECT * FROM source_instances WHERE canonical_source_id=? ORDER BY created_utc",(source_id,)).fetchall(); authors=c.execute("SELECT author_id,display_name,normalized_name,position FROM source_authors WHERE canonical_source_id=? ORDER BY position",(source_id,)).fetchall(); institutions=c.execute("SELECT institution_id,display_name,normalized_name FROM source_institutions WHERE canonical_source_id=? ORDER BY display_name",(source_id,)).fetchall()
            return self._assemble(row,ids,instances,authors,institutions)

    def _assemble(self,row:Any,ids:list[Any],instances:list[Any],authors:list[Any],institutions:list[Any])->dict[str,Any]:
        base=self._row_dict(row); grouped={kind:[] for kind in IDENTITY_PRIORITY}
        for x in ids: grouped.setdefault(str(x["identifier_type"]),[]).append(str(x["identifier_value"]))
        base.update({"schema":SOURCE_IDENTITY_SCHEMA,"identifiers":grouped,"instances":[self._row_dict(x) for x in instances],"authors":[dict(x) for x in authors],"institutions":[dict(x) for x in institutions]})
        return base

    def graph(self,source_id:str,limit:int=200)->dict[str,Any]:
        limit=max(1,min(1000,int(limit)))
        if not self.get(source_id): return {}
        if self.backend=="postgres":
            with self._postgres() as c:
                outgoing=c.execute("SELECT * FROM sc_rl_citation_edges WHERE citing_source_id=%s ORDER BY reference_index NULLS LAST LIMIT %s",(source_id,limit)).fetchall(); incoming=c.execute("SELECT * FROM sc_rl_citation_edges WHERE cited_source_id=%s ORDER BY created_utc DESC LIMIT %s",(source_id,limit)).fetchall(); c.commit()
        else:
            with self._sqlite() as c:
                outgoing=c.execute("SELECT * FROM citation_edges WHERE citing_source_id=? ORDER BY reference_index LIMIT ?",(source_id,limit)).fetchall(); incoming=c.execute("SELECT * FROM citation_edges WHERE cited_source_id=? ORDER BY created_utc DESC LIMIT ?",(source_id,limit)).fetchall()
        return {"schema":CITATION_GRAPH_SCHEMA,"canonical_source_id":source_id,"outgoing":[self._row_dict(x) for x in outgoing],"incoming":[self._row_dict(x) for x in incoming],"outgoing_count":len(outgoing),"incoming_count":len(incoming)}


_STORE: SourceGraphStore | None = None
_STORE_LOCK = threading.Lock()

def get_source_graph_store() -> SourceGraphStore:
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = SourceGraphStore()
    return _STORE
