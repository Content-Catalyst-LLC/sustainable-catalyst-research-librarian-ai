from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.ai_research_experiment import (
    AI_RESEARCH_EXPERIMENT_SCHEMA, AI_RESEARCH_TRIAL_SCHEMA, AI_EXPERIMENT_HANDOFF_SCHEMA,
    AI_EXPERIMENT_RUN_RECEIPT_SCHEMA, AI_EXPERIMENT_EVALUATION_BINDING_SCHEMA, AI_EXPERIMENT_SNAPSHOT_SCHEMA,
    AIResearchExperimentCreateRequest, AIResearchTrialCreateRequest, AIExperimentExecutionHandoffRequest,
    AIExperimentRunReceiptRequest, AIExperimentEvaluationBindingRequest, AIExperimentStateRequest,
    AIExperimentSnapshotRequest,
)
from .ai_research_context import get_ai_research_context_store
from .rag_evaluation import get_rag_evaluation_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None

def _json(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v:Any)->str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now()->str: return datetime.now(timezone.utc).isoformat()

class AIResearchExperimentStore:
    def __init__(self, sqlite_path:Path|None=None, context_store:Any|None=None, evaluation_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"ai_research_experiments.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock(); self.context_store=context_store; self.evaluation_store=evaluation_store
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres AI experiment storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    def _contexts(self): return self.context_store or get_ai_research_context_store()
    def _evaluations(self): return self.evaluation_store or get_rag_evaluation_store()

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
CREATE TABLE IF NOT EXISTS ai_research_experiments(experiment_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_research_trials(trial_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_experiment_handoffs(handoff_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_experiment_run_receipts(receipt_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_experiment_evaluation_bindings(binding_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_experiment_snapshots(snapshot_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_experiment_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,experiment_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_research_experiments(experiment_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_research_trials(trial_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_handoffs(handoff_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_run_receipts(receipt_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_evaluation_bindings(binding_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_snapshots(snapshot_id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_events(event_id BIGSERIAL PRIMARY KEY,experiment_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()

    def _event(self,eid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        h=_sha({"experiment_id":eid,"event_type":typ,"actor_ref":actor,"payload":payload})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_ai_experiment_events(experiment_id,event_type,actor_ref,payload,event_hash) VALUES(%s,%s,%s,%s,%s)",(eid,typ,actor,Jsonb(payload),h)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO ai_experiment_events(experiment_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(eid,typ,actor,_json(payload),h,_now()))

    def create_experiment(self,req:AIResearchExperimentCreateRequest)->dict[str,Any]:
        if req.base_context_id: self._contexts().get_context(req.base_context_id)
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; eid="aiexp-"+_sha(body)[:32]
        rec={"schema":AI_RESEARCH_EXPERIMENT_SCHEMA,"experiment_id":eid,**body,"state":"draft","created_utc":_now(),"governance":{"core_ai_objects_remain_external":True,"librarian_executes_training":False,"automatic_best_model_selection":False,"human_controls_experiment_state":True}}
        rec["record_hash"]=_sha(rec)
        self._insert_unique("sc_rl_ai_research_experiments","ai_research_experiments","experiment_id",eid,eid,rec)
        self._event(eid,"experiment.created",req.actor_ref,{"record_hash":rec["record_hash"]}); return self.get_experiment(eid)

    def _insert_unique(self,pg:str,sq:str,idcol:str,item_id:str,eid:str,rec:dict[str,Any])->None:
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(f"INSERT INTO {pg}({idcol},experiment_id,record,record_hash) VALUES(%s,%s,%s,%s) ON CONFLICT({idcol}) DO NOTHING" if idcol!="experiment_id" else f"INSERT INTO {pg}({idcol},record,record_hash) VALUES(%s,%s,%s) ON CONFLICT({idcol}) DO NOTHING", (item_id,eid,Jsonb(rec),rec["record_hash"]) if idcol!="experiment_id" else (item_id,Jsonb(rec),rec["record_hash"])); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                if idcol=="experiment_id": c.execute(f"INSERT OR IGNORE INTO {sq}({idcol},record_json,record_hash,created_utc) VALUES(?,?,?,?)",(item_id,_json(rec),rec["record_hash"],rec["created_utc"]))
                else: c.execute(f"INSERT OR IGNORE INTO {sq}({idcol},experiment_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?)",(item_id,eid,_json(rec),rec["record_hash"],rec["created_utc"]))

    def get_experiment(self,eid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_ai_research_experiments WHERE experiment_id=%s",(eid,)).fetchone(); rec=dict(row["record"]) if row else None
        else:
            with self._sqlite() as c: row=c.execute("SELECT record_json FROM ai_research_experiments WHERE experiment_id=?",(eid,)).fetchone(); rec=json.loads(row["record_json"]) if row else None
        if not rec: raise ValueError(f"Unknown AI research experiment: {eid}")
        return rec

    def _records(self,pg:str,sq:str,eid:str)->list[dict[str,Any]]:
        self.get_experiment(eid)
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute(f"SELECT record FROM {pg} WHERE experiment_id=%s ORDER BY created_utc",(eid,)).fetchall(); return [dict(x["record"]) for x in rows]
        with self._sqlite() as c: rows=c.execute(f"SELECT record_json FROM {sq} WHERE experiment_id=? ORDER BY created_utc",(eid,)).fetchall(); return [json.loads(x["record_json"]) for x in rows]

    def trials(self,eid:str): return self._records("sc_rl_ai_research_trials","ai_research_trials",eid)
    def handoffs(self,eid:str): return self._records("sc_rl_ai_experiment_handoffs","ai_experiment_handoffs",eid)
    def receipts(self,eid:str): return self._records("sc_rl_ai_experiment_run_receipts","ai_experiment_run_receipts",eid)
    def bindings(self,eid:str): return self._records("sc_rl_ai_experiment_evaluation_bindings","ai_experiment_evaluation_bindings",eid)

    def add_trial(self,eid:str,req:AIResearchTrialCreateRequest)->dict[str,Any]:
        self.get_experiment(eid)
        if req.context_id: self._contexts().get_context(req.context_id)
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; tid="aitrial-"+_sha({"experiment_id":eid,**body})[:32]
        rec={"schema":AI_RESEARCH_TRIAL_SCHEMA,"trial_id":tid,"experiment_id":eid,**body,"created_utc":_now(),"governance":{"trial_is_declared_configuration":True,"external_ai_object_refs_preserved":True}}
        rec["record_hash"]=_sha(rec); self._insert_unique("sc_rl_ai_research_trials","ai_research_trials","trial_id",tid,eid,rec); self._event(eid,"trial.registered",req.actor_ref,{"trial_id":tid}); return rec

    def _trial(self,eid:str,tid:str)->dict[str,Any]:
        for x in self.trials(eid):
            if x["trial_id"]==tid: return x
        raise ValueError(f"Unknown trial for experiment: {tid}")

    def create_handoff(self,eid:str,req:AIExperimentExecutionHandoffRequest)->dict[str,Any]:
        trial=self._trial(eid,req.trial_id); body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; hid="aihandoff-"+_sha({"experiment_id":eid,**body})[:32]
        rec={"schema":AI_EXPERIMENT_HANDOFF_SCHEMA,"handoff_id":hid,"experiment_id":eid,**body,"trial_hash":trial["record_hash"],"created_utc":_now(),"governance":{"handoff_is_request_not_execution_receipt":True,"external_runtime_executes":True,"automatic_execution":False}}
        rec["record_hash"]=_sha(rec); self._insert_unique("sc_rl_ai_experiment_handoffs","ai_experiment_handoffs","handoff_id",hid,eid,rec); self._event(eid,"execution-handoff.created",req.actor_ref,{"handoff_id":hid,"trial_id":req.trial_id}); return rec

    def add_receipt(self,eid:str,req:AIExperimentRunReceiptRequest)->dict[str,Any]:
        trial=self._trial(eid,req.trial_id)
        if req.handoff_id and not any(x["handoff_id"]==req.handoff_id for x in self.handoffs(eid)): raise ValueError(f"Unknown handoff for experiment: {req.handoff_id}")
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; rid="aireceipt-"+_sha({"experiment_id":eid,**body})[:32]
        rec={"schema":AI_EXPERIMENT_RUN_RECEIPT_SCHEMA,"receipt_id":rid,"experiment_id":eid,**body,"trial_hash":trial["record_hash"],"created_utc":_now(),"governance":{"receipt_is_external_execution_record":True,"success_not_inferred":True,"metrics_are_descriptive":True}}
        rec["record_hash"]=_sha(rec); self._insert_unique("sc_rl_ai_experiment_run_receipts","ai_experiment_run_receipts","receipt_id",rid,eid,rec); self._event(eid,"run-receipt.registered",req.actor_ref,{"receipt_id":rid,"status":req.status}); return rec

    def add_evaluation_binding(self,eid:str,req:AIExperimentEvaluationBindingRequest)->dict[str,Any]:
        self._trial(eid,req.trial_id); self._evaluations().get_evaluation(req.evaluation_id)
        if req.run_receipt_id and not any(x["receipt_id"]==req.run_receipt_id for x in self.receipts(eid)): raise ValueError(f"Unknown run receipt for experiment: {req.run_receipt_id}")
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; bid="aievalbind-"+_sha({"experiment_id":eid,**body})[:32]
        rec={"schema":AI_EXPERIMENT_EVALUATION_BINDING_SCHEMA,"binding_id":bid,"experiment_id":eid,**body,"created_utc":_now(),"governance":{"evaluation_is_evidence_not_winner_selection":True,"human_interpretation_required":True}}
        rec["record_hash"]=_sha(rec); self._insert_unique("sc_rl_ai_experiment_evaluation_bindings","ai_experiment_evaluation_bindings","binding_id",bid,eid,rec); self._event(eid,"evaluation.bound",req.actor_ref,{"binding_id":bid,"evaluation_id":req.evaluation_id}); return rec

    def set_state(self,eid:str,req:AIExperimentStateRequest)->dict[str,Any]:
        rec=self.get_experiment(eid); old=rec["state"]
        allowed={"draft":{"ready","cancelled"},"ready":{"running","cancelled"},"running":{"paused","completed","cancelled"},"paused":{"running","cancelled"},"completed":set(),"cancelled":set()}
        if req.state!=old and req.state not in allowed.get(old,set()): raise ValueError(f"Invalid experiment state transition: {old} -> {req.state}")
        if req.state=="ready" and not self.trials(eid): raise ValueError("Experiment cannot be ready without at least one trial.")
        rec={**rec,"state":req.state,"updated_utc":_now(),"state_note":req.note}; rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("UPDATE sc_rl_ai_research_experiments SET record=%s,record_hash=%s WHERE experiment_id=%s",(Jsonb(rec),rec["record_hash"],eid)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("UPDATE ai_research_experiments SET record_json=?,record_hash=? WHERE experiment_id=?",(_json(rec),rec["record_hash"],eid))
        self._event(eid,"state.changed",req.actor_ref,{"from":old,"to":req.state}); return rec

    def summary(self,eid:str)->dict[str,Any]:
        exp=self.get_experiment(eid); trials=self.trials(eid); receipts=self.receipts(eid); bindings=self.bindings(eid); handoffs=self.handoffs(eid)
        by_status={s:sum(1 for r in receipts if r.get("status")==s) for s in ["queued","running","succeeded","failed","cancelled"]}
        return {"schema":"sc-research-librarian-ai-experiment-summary/1.0","experiment_id":eid,"state":exp["state"],"counts":{"trials":len(trials),"handoffs":len(handoffs),"run_receipts":len(receipts),"evaluation_bindings":len(bindings)},"run_status_counts":by_status,"trial_ids":[x["trial_id"] for x in trials],"evaluation_ids":[x["evaluation_id"] for x in bindings],"governance":{"descriptive_only":True,"winner_selected":False,"ranking_generated":False,"automatic_causal_inference":False,"human_interpretation_required":True}}

    def freeze_snapshot(self,req:AIExperimentSnapshotRequest)->dict[str,Any]:
        payload={"schema":AI_EXPERIMENT_SNAPSHOT_SCHEMA,"experiment":self.get_experiment(req.experiment_id),"trials":self.trials(req.experiment_id),"handoffs":self.handoffs(req.experiment_id),"run_receipts":self.receipts(req.experiment_id),"evaluation_bindings":self.bindings(req.experiment_id),"summary":self.summary(req.experiment_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducibility_record_not_model_certification":True}}
        h=_sha(payload); sid="aiexpsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_ai_experiment_snapshots(snapshot_id,experiment_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.experiment_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO ai_experiment_snapshots(snapshot_id,experiment_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.experiment_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.experiment_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":AI_RESEARCH_EXPERIMENT_SCHEMA,"release":settings.release_version,"durable":True,"experiment_components":["experiment-definition","trial-configuration","execution-handoff","run-receipt","evaluation-binding","reproducibility-snapshot"],"execution_targets":["workspace","research-lab","workbench","external"],"core_ai_object_refs_are_external":True,"automatic_execution":False,"model_training_execution":False,"automatic_best_model_selection":False,"automatic_causal_inference":False,"human_controls_experiment_state":True,"human_interpretation_required":True}

_store:AIResearchExperimentStore|None=None
def get_ai_research_experiment_store()->AIResearchExperimentStore:
    global _store
    if _store is None: _store=AIResearchExperimentStore()
    return _store
