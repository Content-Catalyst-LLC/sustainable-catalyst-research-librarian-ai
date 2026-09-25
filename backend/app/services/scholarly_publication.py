from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading, uuid
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.scholarly_publication import (
    SCHOLARLY_PUBLICATION_SCHEMA, SCHOLARLY_PUBLICATION_PACKAGE_SCHEMA,
    SCHOLARLY_DISSEMINATION_READINESS_SCHEMA, KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA,
    CITATION_EXPORT_SCHEMA, ScholarlyPublicationCreateRequest, PublicationVersionRequest,
    PublicationIdentifierRequest, PublicationStateTransitionRequest, PublicationHandoffRequest,
    PublicationPackageFreezeRequest,
)
from .scholarly_research import get_scholarly_research_store
from .peer_review import get_peer_review_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None


def _json(v: Any) -> str: return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",",":"), default=str)
def _sha(v: Any) -> str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _uid(prefix: str) -> str: return f"{prefix}-{uuid.uuid4().hex}"


class ScholarlyPublicationStore:
    def __init__(self, sqlite_path: Path | None=None) -> None:
        self.backend="postgres" if settings.database_backend=="postgres" else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"scholarly_publication.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres publication storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self,migration: bool=False) -> Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self) -> None:
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS scholarly_publications(publication_id TEXT PRIMARY KEY,study_id TEXT NOT NULL,record_json TEXT NOT NULL,record_fingerprint TEXT NOT NULL,idempotency_key TEXT NOT NULL DEFAULT '',created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scholarly_publications_idempotency ON scholarly_publications(idempotency_key) WHERE idempotency_key<>'';
CREATE TABLE IF NOT EXISTS scholarly_publication_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,publication_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL DEFAULT '',payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scholarly_publication_packages(package_id TEXT PRIMARY KEY,publication_id TEXT NOT NULL,package_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_scholarly_publications(publication_id TEXT PRIMARY KEY,study_id TEXT NOT NULL,record JSONB NOT NULL,record_fingerprint TEXT NOT NULL,idempotency_key TEXT NOT NULL DEFAULT '',created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_scholarly_publications_idempotency ON sc_rl_scholarly_publications(idempotency_key) WHERE idempotency_key<>''")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_scholarly_publication_events(event_id BIGSERIAL PRIMARY KEY,publication_id TEXT NOT NULL REFERENCES sc_rl_scholarly_publications(publication_id) ON DELETE CASCADE,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL DEFAULT '',payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_scholarly_publication_packages(package_id TEXT PRIMARY KEY,publication_id TEXT NOT NULL REFERENCES sc_rl_scholarly_publications(publication_id) ON DELETE CASCADE,package_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.commit()

    def _load(self,pid:str)->dict[str,Any]|None:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_scholarly_publications WHERE publication_id=%s",(pid,)).fetchone(); c.commit()
            return dict(row["record"]) if row else None
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM scholarly_publications WHERE publication_id=?",(pid,)).fetchone()
        return json.loads(row["record_json"]) if row else None

    def _event(self,pid,event_type,actor,payload):
        created=_now(); h=_sha({"publication_id":pid,"event_type":event_type,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_publication_events(publication_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,event_type,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO scholarly_publication_events(publication_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,event_type,actor,_json(payload),h,created))

    def _save(self,rec,event_type,actor,payload):
        item=json.loads(_json(rec)); item["release"]=settings.release_version; item["updated_utc"]=_now(); item["record_fingerprint"]=_sha({k:v for k,v in item.items() if k not in {"record_fingerprint","updated_utc"}})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("UPDATE sc_rl_scholarly_publications SET record=%s,record_fingerprint=%s,updated_utc=%s WHERE publication_id=%s",(Jsonb(item),item["record_fingerprint"],item["updated_utc"],item["publication_id"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("UPDATE scholarly_publications SET record_json=?,record_fingerprint=?,updated_utc=? WHERE publication_id=?",(_json(item),item["record_fingerprint"],item["updated_utc"],item["publication_id"]))
        self._event(item["publication_id"],event_type,actor,payload); return item

    def create(self,study_id:str,request:ScholarlyPublicationCreateRequest)->tuple[dict[str,Any],bool]:
        study=get_scholarly_research_store().get(study_id)
        if not get_scholarly_research_store().readiness(study_id)["ready"]: raise ValueError("Study is not publication-ready.")
        key=(request.idempotency_key or "").strip()
        if key:
            rows=self.list(study_id=study_id,limit=500)
            for r in rows:
                if r.get("idempotency_key")==key: return r,True
        now=_now(); pid=_uid("publication")
        rec={"schema":SCHOLARLY_PUBLICATION_SCHEMA,"release":settings.release_version,"publication_id":pid,"study_id":study_id,"core_project_id":study["core_project_id"],**request.model_dump(mode="json"),"state":"draft","version":1,"versions":[],"identifiers":[],"state_history":[],"knowledge_library_handoffs":[],"created_utc":now,"updated_utc":now}
        rec["versions"].append({"version":1,"version_label":"initial","actor_ref":request.actor_ref,"title":request.title,"abstract":request.abstract,"keywords":request.keywords,"manuscript_artifact_ref":request.manuscript_artifact_ref,"visual_refs":request.visual_refs,"content_hash":_sha({"title":request.title,"abstract":request.abstract,"references":[r.model_dump(mode="json") for r in request.references],"manuscript_artifact_ref":request.manuscript_artifact_ref}),"created_utc":now})
        rec["record_fingerprint"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_publications(publication_id,study_id,record,record_fingerprint,idempotency_key,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s,%s)",(pid,study_id,Jsonb(rec),rec["record_fingerprint"],key,now,now)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO scholarly_publications(publication_id,study_id,record_json,record_fingerprint,idempotency_key,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?)",(pid,study_id,_json(rec),rec["record_fingerprint"],key,now,now))
        self._event(pid,"publication-created",request.actor_ref,{"study_id":study_id,"version":1}); return rec,False

    def get(self,pid:str)->dict[str,Any]:
        rec=self._load(pid)
        if not rec: raise KeyError(pid)
        return rec

    def list(self,study_id:str="",state:str="",limit:int=100)->list[dict[str,Any]]:
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT record FROM sc_rl_scholarly_publications ORDER BY created_utc DESC LIMIT %s",(max(1,min(limit,1000)),)).fetchall(); c.commit()
            items=[dict(r["record"]) for r in rows]
        else:
            with self._lock,self._sqlite() as c: rows=c.execute("SELECT record_json FROM scholarly_publications ORDER BY created_utc DESC LIMIT ?",(max(1,min(limit,1000)),)).fetchall()
            items=[json.loads(r["record_json"]) for r in rows]
        if study_id: items=[x for x in items if x.get("study_id")==study_id]
        if state: items=[x for x in items if x.get("state")==state]
        return items

    def add_version(self,pid:str,request:PublicationVersionRequest)->dict[str,Any]:
        rec=self.get(pid); v=int(rec.get("version",1))+1
        item={"version":v,"version_label":request.version_label,"actor_ref":request.actor_ref,"change_summary":request.change_summary,"title":request.title or rec["title"],"abstract":request.abstract or rec["abstract"],"keywords":request.keywords or rec.get("keywords",[]),"manuscript_artifact_ref":request.manuscript_artifact_ref or rec.get("manuscript_artifact_ref",""),"visual_refs":request.visual_refs or rec.get("visual_refs",[]),"metadata":request.metadata,"created_utc":_now()}; item["content_hash"]=_sha(item)
        rec["versions"].append(item); rec["version"]=v
        if request.title: rec["title"]=request.title
        if request.abstract: rec["abstract"]=request.abstract
        if request.keywords: rec["keywords"]=request.keywords
        if request.manuscript_artifact_ref: rec["manuscript_artifact_ref"]=request.manuscript_artifact_ref
        if request.visual_refs: rec["visual_refs"]=request.visual_refs
        return self._save(rec,"publication-version-added",request.actor_ref,{"version":v,"content_hash":item["content_hash"]})

    def add_identifier(self,pid:str,request:PublicationIdentifierRequest)->dict[str,Any]:
        rec=self.get(pid); value=request.value.strip()
        if any(i.get("identifier_type")==request.identifier_type and i.get("value")==value for i in rec["identifiers"]): return rec
        item={"identifier_id":_uid("identifier"),**request.model_dump(mode="json"),"declared_external_identifier":request.identifier_type!="local","assigned_by_librarian":False,"created_utc":_now()}; item["identifier_hash"]=_sha(item); rec["identifiers"].append(item)
        return self._save(rec,"publication-identifier-recorded",request.actor_ref,{"identifier_id":item["identifier_id"],"identifier_type":item["identifier_type"]})

    def transition(self,pid:str,request:PublicationStateTransitionRequest)->dict[str,Any]:
        rec=self.get(pid)
        allowed={"draft":{"submitted","withdrawn"},"submitted":{"accepted","withdrawn","draft"},"accepted":{"published","withdrawn"},"published":{"superseded","withdrawn"},"withdrawn":set(),"superseded":set()}
        cur=rec["state"]
        if request.state==cur: return rec
        if request.state not in allowed.get(cur,set()): raise ValueError(f"Invalid publication state transition {cur!r} -> {request.state!r}.")
        if request.state in {"accepted","published"} and not request.decision_ref.strip(): raise ValueError("decision_ref is required for accepted/published state.")
        if request.state=="published" and not request.canonical_url.strip(): raise ValueError("canonical_url is required for published state.")
        item={**request.model_dump(mode="json"),"from_state":cur,"created_utc":_now()}; item["transition_hash"]=_sha(item)
        rec["state"]=request.state; rec["state_history"].append(item)
        if request.venue: rec["venue"]=request.venue
        if request.canonical_url: rec["canonical_url"]=request.canonical_url
        if request.publication_date: rec["publication_date"]=request.publication_date
        return self._save(rec,"publication-state-transition",request.actor_ref,{"from_state":cur,"to_state":request.state,"transition_hash":item["transition_hash"]})

    def citation_exports(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); authors=[c["display_name"] for c in rec.get("contributors",[]) if c.get("role")=="author"]
        ids={i["identifier_type"]:i["value"] for i in rec.get("identifiers",[])}
        csl={"id":pid,"type":"article-journal" if rec.get("publication_type")=="article" else "report","title":rec["title"],"author":[{"literal":a} for a in authors],"URL":rec.get("canonical_url","")}
        if ids.get("doi"): csl["DOI"]=ids["doi"]
        if rec.get("publication_date"): csl["issued"]={"raw":rec["publication_date"]}
        author_text=" and ".join(authors) or "Declared authors"
        bib_key="sc_"+pid.replace("-","")[:18]
        bib=f"@misc{{{bib_key},\n  title = {{{rec['title']}}},\n  author = {{{author_text}}},\n  url = {{{rec.get('canonical_url','')}}}" + (f",\n  doi = {{{ids['doi']}}}" if ids.get("doi") else "") + "\n}"
        return {"schema":CITATION_EXPORT_SCHEMA,"publication_id":pid,"csl_json":csl,"bibtex":bib,"identifiers":ids,"governance":{"identifiers_are_declared_not_minted":True}}

    def readiness(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); study=get_scholarly_research_store().readiness(rec["study_id"])
        blockers=[]
        if not study["ready"]: blockers.append("study_publication_readiness")
        if not any(c.get("role")=="author" for c in rec.get("contributors",[])): blockers.append("author_declared")
        if not rec.get("abstract","").strip(): blockers.append("abstract_present")
        if not rec.get("manuscript_artifact_ref","").strip(): blockers.append("manuscript_artifact_ref")
        if rec.get("state") in {"accepted","published"}:
            try:
                pr=get_peer_review_store().readiness(rec["study_id"])
                if not pr.get("ready"): blockers.append("peer_review_validation_readiness")
            except Exception:
                blockers.append("peer_review_validation_readiness")
        if rec.get("state")=="published" and not rec.get("canonical_url","").strip(): blockers.append("canonical_url")
        return {"schema":SCHOLARLY_DISSEMINATION_READINESS_SCHEMA,"publication_id":pid,"ready":not blockers,"blockers":blockers,"study_readiness":study,"state":rec["state"],"governance":{"readiness_is_not_editorial_acceptance":True,"doi_not_required":True,"automatic_publication":False}}

    def knowledge_library_handoff(self,pid:str,request:PublicationHandoffRequest)->dict[str,Any]:
        rec=self.get(pid); exports=self.citation_exports(pid) if request.include_citation_exports else {}
        handoff={"schema":KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA,"handoff_id":_uid("library-handoff"),"publication_id":pid,"study_id":rec["study_id"],"collection_ref":request.collection_ref,"actor_ref":request.actor_ref,"title":rec["title"],"subtitle":rec.get("subtitle",""),"abstract":rec["abstract"],"keywords":rec.get("keywords",[]),"contributors":rec.get("contributors",[]),"references":rec.get("references",[]),"source_refs":rec.get("source_refs",[]),"core_evidence_refs":rec.get("core_evidence_refs",[]),"core_research_object_refs":rec.get("core_research_object_refs",[]),"visual_refs":rec.get("visual_refs",[]) if request.include_visualizations else [],"canonical_url":rec.get("canonical_url",""),"identifiers":rec.get("identifiers",[]),"citation_exports":exports,"note":request.note,"created_utc":_now(),"status":"ready-for-explicit-library-import","governance":{"handoff_does_not_publish_automatically":True,"source_and_research_lineage_preserved":True}}; handoff["handoff_hash"]=_sha(handoff)
        rec["knowledge_library_handoffs"].append(handoff)
        self._save(rec,"knowledge-library-handoff-created",request.actor_ref,{"handoff_id":handoff["handoff_id"],"handoff_hash":handoff["handoff_hash"]}); return handoff

    def freeze_package(self,pid:str,request:PublicationPackageFreezeRequest)->dict[str,Any]:
        rec=self.get(pid); ready=self.readiness(pid)
        if request.require_publication_ready and not ready["ready"]: raise ValueError(f"Publication is not dissemination-ready; blockers={ready['blockers']}")
        if request.require_published_state and rec.get("state")!="published": raise ValueError("Publication must be in published state.")
        package={"schema":SCHOLARLY_PUBLICATION_PACKAGE_SCHEMA,"package_id":_uid("publication-package"),"publication_id":pid,"study_id":rec["study_id"],"package_label":request.package_label,"publication":rec,"citation_exports":self.citation_exports(pid),"dissemination_readiness":ready,"knowledge_library_handoffs":rec.get("knowledge_library_handoffs",[]),"core_publication_object_plan":{"object_type":"publication","core_project_id":rec["core_project_id"],"source_local_ref":pid,"explicit_core_promotion_required":True},"actor_ref":request.actor_ref,"note":request.note,"created_utc":_now(),"governance":{"package_is_not_peer_review_certification":True,"package_is_not_doi_registration":True,"package_does_not_publish_automatically":True,"authorship_is_human_declared":True}}; package["package_hash"]=_sha(package)
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_publication_packages(package_id,publication_id,package_hash,record,created_utc) VALUES(%s,%s,%s,%s,%s)",(package["package_id"],pid,package["package_hash"],Jsonb(package),package["created_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO scholarly_publication_packages(package_id,publication_id,package_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(package["package_id"],pid,package["package_hash"],_json(package),package["created_utc"]))
        self._event(pid,"publication-package-frozen",request.actor_ref,{"package_id":package["package_id"],"package_hash":package["package_hash"]}); return package

    def events(self,pid:str,limit:int=500)->list[dict[str,Any]]:
        self.get(pid)
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT event_id,event_type,actor_ref,payload,event_hash,created_utc FROM sc_rl_scholarly_publication_events WHERE publication_id=%s ORDER BY event_id DESC LIMIT %s",(pid,max(1,min(limit,2000)))).fetchall(); c.commit()
            return [{**dict(r),"payload":dict(r["payload"])} for r in rows]
        with self._lock,self._sqlite() as c: rows=c.execute("SELECT event_id,event_type,actor_ref,payload_json,event_hash,created_utc FROM scholarly_publication_events WHERE publication_id=? ORDER BY event_id DESC LIMIT ?",(pid,max(1,min(limit,2000)))).fetchall()
        return [{"event_id":r["event_id"],"event_type":r["event_type"],"actor_ref":r["actor_ref"],"payload":json.loads(r["payload_json"]),"event_hash":r["event_hash"],"created_utc":r["created_utc"]} for r in rows]

    def packages(self,pid:str,limit:int=100)->list[dict[str,Any]]:
        self.get(pid)
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT record FROM sc_rl_scholarly_publication_packages WHERE publication_id=%s ORDER BY created_utc DESC LIMIT %s",(pid,max(1,min(limit,1000)))).fetchall(); c.commit()
            return [dict(r["record"]) for r in rows]
        with self._lock,self._sqlite() as c: rows=c.execute("SELECT record_json FROM scholarly_publication_packages WHERE publication_id=? ORDER BY created_utc DESC LIMIT ?",(pid,max(1,min(limit,1000)))).fetchall()
        return [json.loads(r["record_json"]) for r in rows]


_pub_store: ScholarlyPublicationStore|None=None
def get_scholarly_publication_store()->ScholarlyPublicationStore:
    global _pub_store
    if _pub_store is None: _pub_store=ScholarlyPublicationStore()
    return _pub_store

def capabilities()->dict[str,Any]:
    return {"schema":SCHOLARLY_PUBLICATION_SCHEMA,"release":settings.release_version,"durable_publication_registry":True,"versioned_publication_records":True,"structured_reference_registry":True,"citation_exports":True,"knowledge_library_handoff":True,"publication_visualization_lineage":True,"canonical_url_registry":True,"declared_external_identifier_registry":True,"doi_minting":False,"automatic_authorship":False,"automatic_editorial_acceptance":False,"automatic_publication":False,"automatic_core_writes":False,"automatic_truth_promotion":False}
