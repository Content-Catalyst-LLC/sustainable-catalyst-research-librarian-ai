from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.model_aware_exchange import (
    MODEL_AWARE_RESEARCH_SCHEMA, CROSS_PRODUCT_EXCHANGE_SCHEMA,
    CROSS_PRODUCT_EXCHANGE_RECEIPT_SCHEMA, MODEL_AWARE_SNAPSHOT_SCHEMA,
    ModelAwareResearchRecordRequest, CrossProductExchangeCreateRequest,
    CrossProductExchangeReceiptRequest, ModelAwareSnapshotRequest,
)
from .ai_research_context import get_ai_research_context_store
from .rag_evaluation import get_rag_evaluation_store
from .ai_research_experiment import get_ai_research_experiment_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None

def _json(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v:Any)->str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now()->str: return datetime.now(timezone.utc).isoformat()
def _uniq(values:list[str])->list[str]: return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))

_DESTINATION_CONTRACTS={
    "platform-core":"sc.core.exchange-package.v1",
    "workspace":"sc.workspace.research-exchange.v1",
    "research-lab":"sc.lab.research-exchange.v1",
    "workbench":"sc.workbench.research-exchange.v1",
    "knowledge-library":"sc.library.research-exchange.v1",
    "decision-studio":"sc.decision-studio.research-exchange.v1",
    "site-intelligence":"sc.site-intelligence.research-exchange.v1",
}

class ModelAwareResearchStore:
    def __init__(self, sqlite_path:Path|None=None, context_store:Any|None=None, evaluation_store:Any|None=None, experiment_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"model_aware_exchange.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock(); self.context_store=context_store; self.evaluation_store=evaluation_store; self.experiment_store=experiment_store
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres model-aware exchange storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    def _contexts(self): return self.context_store or get_ai_research_context_store()
    def _evaluations(self): return self.evaluation_store or get_rag_evaluation_store()
    def _experiments(self): return self.experiment_store or get_ai_research_experiment_store()

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
CREATE TABLE IF NOT EXISTS model_aware_research_records(record_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cross_product_exchanges(exchange_id TEXT PRIMARY KEY,record_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cross_product_exchange_receipts(receipt_id TEXT PRIMARY KEY,exchange_id TEXT NOT NULL,record_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_aware_research_snapshots(snapshot_id TEXT PRIMARY KEY,record_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_aware_research_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,record_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_model_aware_research_records(record_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_cross_product_exchanges(exchange_id TEXT PRIMARY KEY,record_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_product_exchanges_record ON sc_rl_cross_product_exchanges(record_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_cross_product_exchange_receipts(receipt_id TEXT PRIMARY KEY,exchange_id TEXT NOT NULL,record_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_product_receipts_exchange ON sc_rl_cross_product_exchange_receipts(exchange_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_model_aware_research_snapshots(snapshot_id TEXT PRIMARY KEY,record_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_model_aware_research_events(event_id BIGSERIAL PRIMARY KEY,record_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_model_aware_events_record ON sc_rl_model_aware_research_events(record_id,created_utc)",
            ]: c.execute(ddl)
            c.commit()

    def _event(self,record_id:str,event_type:str,actor_ref:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"record_id":record_id,"event_type":event_type,"actor_ref":actor_ref,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_model_aware_research_events(record_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(record_id,event_type,actor_ref,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO model_aware_research_events(record_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(record_id,event_type,actor_ref,_json(payload),h,created))

    def _insert(self,pg_table:str,sqlite_table:str,id_col:str,item_id:str,record_id:str,rec:dict[str,Any])->None:
        if self.backend=="postgres":
            with self._postgres() as c:
                if id_col=="record_id": c.execute(f"INSERT INTO {pg_table}({id_col},record,record_hash) VALUES(%s,%s,%s) ON CONFLICT({id_col}) DO NOTHING",(item_id,Jsonb(rec),rec["record_hash"]))
                else: c.execute(f"INSERT INTO {pg_table}({id_col},record_id,record,record_hash) VALUES(%s,%s,%s,%s) ON CONFLICT({id_col}) DO NOTHING",(item_id,record_id,Jsonb(rec),rec["record_hash"]))
                c.commit()
        else:
            with self._lock,self._sqlite() as c:
                if id_col=="record_id": c.execute(f"INSERT OR IGNORE INTO {sqlite_table}({id_col},record_json,record_hash,created_utc) VALUES(?,?,?,?)",(item_id,_json(rec),rec["record_hash"],rec["created_utc"]))
                else: c.execute(f"INSERT OR IGNORE INTO {sqlite_table}({id_col},record_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?)",(item_id,record_id,_json(rec),rec["record_hash"],rec["created_utc"]))

    def _get(self,pg_table:str,sqlite_table:str,id_col:str,item_id:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute(f"SELECT record FROM {pg_table} WHERE {id_col}=%s",(item_id,)).fetchone()
                if not row: raise KeyError(item_id)
                return dict(row["record"])
        with self._lock,self._sqlite() as c:
            row=c.execute(f"SELECT record_json FROM {sqlite_table} WHERE {id_col}=?",(item_id,)).fetchone()
            if not row: raise KeyError(item_id)
            return json.loads(row["record_json"])

    def create_record(self,req:ModelAwareResearchRecordRequest)->dict[str,Any]:
        if req.context_id: self._contexts().get_context(req.context_id)
        if req.experiment_id: self._experiments().get_experiment(req.experiment_id)
        for eid in _uniq(req.evaluation_ids): self._evaluations().get_evaluation(eid)
        body=req.model_dump(); actor=body.pop("actor_ref")
        for key in ["evaluation_ids","evidence_refs","claim_refs","finding_refs","statistical_refs","visual_refs","artifact_refs"]: body[key]=_uniq(body[key])
        rid="mair-"+_sha(body)[:32]
        rec={"schema":MODEL_AWARE_RESEARCH_SCHEMA,"record_id":rid,**body,"created_utc":_now(),"governance":{"core_ai_objects_remain_external":True,"lineage_is_descriptive_not_quality_judgment":True,"automatic_model_registration":False,"automatic_model_selection":False,"automatic_truth_promotion":False}}
        rec["record_hash"]=_sha(rec); self._insert("sc_rl_model_aware_research_records","model_aware_research_records","record_id",rid,rid,rec); self._event(rid,"record.created",actor,{"record_hash":rec["record_hash"]}); return self.get_record(rid)

    def get_record(self,rid:str)->dict[str,Any]: return self._get("sc_rl_model_aware_research_records","model_aware_research_records","record_id",rid)

    def lineage(self,rid:str)->dict[str,Any]:
        r=self.get_record(rid)
        return {"schema":"sc-research-librarian-model-aware-lineage/1.0","record_id":rid,"research":{"project_ref":r.get("project_ref",""),"study_ref":r.get("study_ref",""),"publication_ref":r.get("publication_ref","")},"ai":{"model_ref":r.get("model_ref",""),"model_version_ref":r.get("model_version_ref",""),"dataset_ref":r.get("dataset_ref",""),"dataset_version_ref":r.get("dataset_version_ref",""),"prompt_ref":r.get("prompt_ref",""),"prompt_version_ref":r.get("prompt_version_ref",""),"context_id":r.get("context_id",""),"inference_run_ref":r.get("inference_run_ref",""),"experiment_id":r.get("experiment_id",""),"evaluation_ids":r.get("evaluation_ids",[])},"research_objects":{"evidence_refs":r.get("evidence_refs",[]),"claim_refs":r.get("claim_refs",[]),"finding_refs":r.get("finding_refs",[]),"statistical_refs":r.get("statistical_refs",[]),"visual_refs":r.get("visual_refs",[]),"artifact_refs":r.get("artifact_refs",[])},"record_hash":r["record_hash"],"governance":{"descriptive_lineage_only":True,"quality_or_truth_not_inferred":True}}

    def exchange_readiness(self,rid:str,destination:str)->dict[str,Any]:
        r=self.get_record(rid); blockers=[]
        if destination not in _DESTINATION_CONTRACTS: blockers.append("unsupported-destination")
        if not (r.get("model_version_ref") or r.get("experiment_id") or r.get("context_id")): blockers.append("ai-lineage-ref-required")
        if destination=="platform-core" and not r.get("project_ref"): blockers.append("project-ref-required-for-core-exchange")
        return {"schema":"sc-research-librarian-cross-product-exchange-readiness/1.0","record_id":rid,"destination":destination,"ready":not blockers,"blockers":blockers,"default_payload_contract":_DESTINATION_CONTRACTS.get(destination,""),"governance":{"readiness_is_structural_not_destination_acceptance":True,"automatic_delivery":False}}

    def create_exchange(self,req:CrossProductExchangeCreateRequest)->dict[str,Any]:
        r=self.get_record(req.record_id); readiness=self.exchange_readiness(req.record_id,req.destination)
        if not readiness["ready"]: raise ValueError("Exchange is not structurally ready: "+", ".join(readiness["blockers"]))
        body=req.model_dump(); actor=body.pop("actor_ref"); sections=_uniq(body.pop("included_sections"))
        if not sections: sections=["research","ai","research_objects"]
        lineage=self.lineage(req.record_id); payload={k:lineage[k] for k in sections if k in lineage}
        packet_core={**body,"included_sections":sections,"payload_contract_ref":body.get("payload_contract_ref") or readiness["default_payload_contract"],"additional_object_refs":_uniq(body.get("additional_object_refs") or []),"source_record_hash":r["record_hash"],"payload":payload}
        xid="xprod-"+_sha(packet_core)[:32]
        rec={"schema":CROSS_PRODUCT_EXCHANGE_SCHEMA,"exchange_id":xid,"record_id":req.record_id,**packet_core,"created_utc":_now(),"governance":{"packet_is_transport_neutral":True,"packet_creation_is_not_delivery":True,"automatic_delivery":False,"destination_acceptance_not_inferred":True}}
        rec["record_hash"]=_sha(rec); self._insert("sc_rl_cross_product_exchanges","cross_product_exchanges","exchange_id",xid,req.record_id,rec); self._event(req.record_id,"exchange.created",actor,{"exchange_id":xid,"destination":req.destination}); return self.get_exchange(xid)

    def get_exchange(self,xid:str)->dict[str,Any]:
        rec=self._get("sc_rl_cross_product_exchanges","cross_product_exchanges","exchange_id",xid); rec["receipts"]=self.receipts(xid); return rec

    def receipts(self,xid:str)->list[dict[str,Any]]:
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT record FROM sc_rl_cross_product_exchange_receipts WHERE exchange_id=%s ORDER BY created_utc",(xid,)).fetchall(); return [dict(x["record"]) for x in rows]
        with self._lock,self._sqlite() as c: rows=c.execute("SELECT record_json FROM cross_product_exchange_receipts WHERE exchange_id=? ORDER BY created_utc",(xid,)).fetchall(); return [json.loads(x["record_json"]) for x in rows]

    def add_receipt(self,xid:str,req:CrossProductExchangeReceiptRequest)->dict[str,Any]:
        ex=self.get_exchange(xid); body=req.model_dump(); actor=body.pop("actor_ref"); body["destination_object_refs"]=_uniq(body["destination_object_refs"])
        rid="xrec-"+_sha({"exchange_id":xid,**body})[:32]
        rec={"schema":CROSS_PRODUCT_EXCHANGE_RECEIPT_SCHEMA,"receipt_id":rid,"exchange_id":xid,"record_id":ex["record_id"],"destination":ex["destination"],**body,"created_utc":_now(),"governance":{"receipt_records_destination_statement":True,"success_not_inferred_from_packet_creation":True,"receipt_is_not_research_validation":True}}
        rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_cross_product_exchange_receipts(receipt_id,exchange_id,record_id,record,record_hash) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(receipt_id) DO NOTHING",(rid,xid,ex["record_id"],Jsonb(rec),rec["record_hash"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO cross_product_exchange_receipts(receipt_id,exchange_id,record_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?,?)",(rid,xid,ex["record_id"],_json(rec),rec["record_hash"],rec["created_utc"]))
        self._event(ex["record_id"],"exchange.receipt",actor,{"exchange_id":xid,"receipt_id":rid,"status":req.status}); return rec

    def freeze_snapshot(self,req:ModelAwareSnapshotRequest)->dict[str,Any]:
        r=self.get_record(req.record_id)
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT record FROM sc_rl_cross_product_exchanges WHERE record_id=%s ORDER BY created_utc",(req.record_id,)).fetchall(); exchanges=[dict(x["record"]) for x in rows]
        else:
            with self._lock,self._sqlite() as c: rows=c.execute("SELECT record_json FROM cross_product_exchanges WHERE record_id=? ORDER BY created_utc",(req.record_id,)).fetchall(); exchanges=[json.loads(x["record_json"]) for x in rows]
        for x in exchanges: x["receipts"]=self.receipts(x["exchange_id"])
        payload={"schema":MODEL_AWARE_SNAPSHOT_SCHEMA,"record":r,"lineage":self.lineage(req.record_id),"exchanges":exchanges,"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_lineage_and_exchange_record_not_model_certification":True}}
        h=_sha(payload); sid="mairsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_model_aware_research_snapshots(snapshot_id,record_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.record_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO model_aware_research_snapshots(snapshot_id,record_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.record_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.record_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":MODEL_AWARE_RESEARCH_SCHEMA,"release":settings.release_version,"durable":True,"lineage_dimensions":["model","model-version","dataset","dataset-version","prompt","prompt-version","research-context","inference-run","evaluation","experiment","evidence","claim","finding","statistical","visual","publication"],"exchange_destinations":list(_DESTINATION_CONTRACTS),"core_ai_object_refs_are_external":True,"automatic_delivery":False,"automatic_model_registration":False,"automatic_model_selection":False,"automatic_research_judgment":False,"destination_acceptance_requires_receipt":True}

_store:ModelAwareResearchStore|None=None
def get_model_aware_research_store()->ModelAwareResearchStore:
    global _store
    if _store is None: _store=ModelAwareResearchStore()
    return _store
