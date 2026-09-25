from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading, uuid
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.ai_research_context import (
    AI_RESEARCH_CONTEXT_SCHEMA, AI_RETRIEVAL_RUN_SCHEMA, AI_CONTEXT_SNAPSHOT_SCHEMA,
    AIResearchContextCreateRequest, AIRetrievalRunCreateRequest, AIContextSnapshotRequest,
)

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None

def _json(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v:Any)->str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now()->str: return datetime.now(timezone.utc).isoformat()
def _uid(prefix:str)->str: return f"{prefix}-{uuid.uuid4().hex}"

class AIResearchContextStore:
    def __init__(self, sqlite_path:Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"ai_research_context.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres AI context storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self,migration:bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS ai_research_contexts(context_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_retrieval_runs(run_id TEXT PRIMARY KEY,context_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_context_snapshots(snapshot_id TEXT PRIMARY KEY,context_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_context_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,context_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_ai_research_contexts(context_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_ai_retrieval_runs(run_id TEXT PRIMARY KEY,context_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_ai_context_snapshots(snapshot_id TEXT PRIMARY KEY,context_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_ai_context_events(event_id BIGSERIAL PRIMARY KEY,context_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.commit()

    def _event(self,context_id:str,event_type:str,actor_ref:str,payload:dict[str,Any])->None:
        h=_sha({"context_id":context_id,"event_type":event_type,"actor_ref":actor_ref,"payload":payload})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_ai_context_events(context_id,event_type,actor_ref,payload,event_hash) VALUES(%s,%s,%s,%s,%s)",(context_id,event_type,actor_ref,Jsonb(payload),h)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO ai_context_events(context_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(context_id,event_type,actor_ref,_json(payload),h,_now()))

    def create_context(self,req:AIResearchContextCreateRequest)->dict[str,Any]:
        identity={k:v for k,v in req.model_dump().items() if k!="actor_ref"}
        context_id="ctx-"+_sha(identity)[:32]
        rec={"schema":AI_RESEARCH_CONTEXT_SCHEMA,"context_id":context_id,**identity,"created_utc":_now(),"governance":{"core_ai_object_refs_are_external":True,"librarian_trains_models":False,"librarian_mints_model_identity":False,"automatic_quality_judgment":False}}
        rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c:
                existing=c.execute("SELECT record FROM sc_rl_ai_research_contexts WHERE context_id=%s",(context_id,)).fetchone()
                if not existing: c.execute("INSERT INTO sc_rl_ai_research_contexts(context_id,record,record_hash) VALUES(%s,%s,%s)",(context_id,Jsonb(rec),rec["record_hash"])); c.commit()
                else: rec=dict(existing["record"])
        else:
            with self._lock,self._sqlite() as c:
                row=c.execute("SELECT record_json FROM ai_research_contexts WHERE context_id=?",(context_id,)).fetchone()
                if row: rec=json.loads(row["record_json"])
                else: c.execute("INSERT INTO ai_research_contexts(context_id,record_json,record_hash,created_utc) VALUES(?,?,?,?)",(context_id,_json(rec),rec["record_hash"],rec["created_utc"]))
        self._event(context_id,"context.created",req.actor_ref,{"record_hash":rec["record_hash"]})
        return rec

    def get_context(self,context_id:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_ai_research_contexts WHERE context_id=%s",(context_id,)).fetchone(); rec=dict(row["record"]) if row else None
        else:
            with self._sqlite() as c: row=c.execute("SELECT record_json FROM ai_research_contexts WHERE context_id=?",(context_id,)).fetchone(); rec=json.loads(row["record_json"]) if row else None
        if not rec: raise ValueError(f"Unknown AI research context: {context_id}")
        return rec

    def register_run(self,req:AIRetrievalRunCreateRequest)->dict[str,Any]:
        context=self.get_context(req.context_id)
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}
        run_id="airun-"+_sha(body)[:32]
        rec={"schema":AI_RETRIEVAL_RUN_SCHEMA,"run_id":run_id,**body,"context_hash":context["record_hash"],"created_utc":_now(),"governance":{"retrieval_scores_are_descriptive":True,"model_output_not_validated":True,"evidence_grounding_not_automatically_certified":True}}
        rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_ai_retrieval_runs(run_id,context_id,record,record_hash) VALUES(%s,%s,%s,%s) ON CONFLICT(run_id) DO NOTHING",(run_id,req.context_id,Jsonb(rec),rec["record_hash"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO ai_retrieval_runs(run_id,context_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?)",(run_id,req.context_id,_json(rec),rec["record_hash"],rec["created_utc"]))
        self._event(req.context_id,"retrieval-run.registered",req.actor_ref,{"run_id":run_id,"record_hash":rec["record_hash"]})
        return rec

    def runs(self,context_id:str,limit:int=100)->list[dict[str,Any]]:
        self.get_context(context_id)
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT record FROM sc_rl_ai_retrieval_runs WHERE context_id=%s ORDER BY created_utc DESC LIMIT %s",(context_id,limit)).fetchall(); return [dict(x["record"]) for x in rows]
        with self._sqlite() as c: rows=c.execute("SELECT record_json FROM ai_retrieval_runs WHERE context_id=? ORDER BY created_utc DESC LIMIT ?",(context_id,limit)).fetchall(); return [json.loads(x["record_json"]) for x in rows]

    def lineage(self,context_id:str)->dict[str,Any]:
        ctx=self.get_context(context_id); runs=self.runs(context_id,500)
        return {"schema":"sc-research-librarian-ai-context-lineage/1.0","context":ctx,"retrieval_runs":runs,"run_count":len(runs),"reproducibility":{"context_hash":ctx["record_hash"],"all_runs_content_hashed":all(bool(x.get("record_hash")) for x in runs)}}

    def freeze_snapshot(self,req:AIContextSnapshotRequest)->dict[str,Any]:
        lineage=self.lineage(req.context_id)
        payload={"schema":AI_CONTEXT_SNAPSHOT_SCHEMA,"context_id":req.context_id,"label":req.label,"note":req.note,"lineage":lineage,"frozen_utc":_now(),"governance":{"snapshot_is_reproducibility_record_not_quality_certification":True}}
        snapshot_hash=_sha(payload); snapshot_id="ctxsnap-"+snapshot_hash[:32]; payload.update({"snapshot_id":snapshot_id,"snapshot_hash":snapshot_hash})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_ai_context_snapshots(snapshot_id,context_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(snapshot_id,req.context_id,snapshot_hash,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO ai_context_snapshots(snapshot_id,context_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(snapshot_id,req.context_id,snapshot_hash,_json(payload),payload["frozen_utc"]))
        self._event(req.context_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":snapshot_id,"snapshot_hash":snapshot_hash})
        return payload

def capabilities()->dict[str,Any]:
    return {"schema":AI_RESEARCH_CONTEXT_SCHEMA,"release":settings.release_version,"durable":True,"context_components":["corpus-version","dataset","chunking-strategy","embedding-model","retriever","reranker","prompt-version","model-version","generation-parameters","retrieved-evidence"],"core_ai_object_refs_are_external":True,"automatic_model_registration":False,"automatic_grounding_certification":False,"automatic_quality_ranking":False,"model_training_execution":False,"human_review_required_for_research_judgment":True}

_store:AIResearchContextStore|None=None
def get_ai_research_context_store()->AIResearchContextStore:
    global _store
    if _store is None: _store=AIResearchContextStore()
    return _store
