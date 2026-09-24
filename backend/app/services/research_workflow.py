from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading, uuid
from pathlib import Path
from typing import Any, Iterator
from ..async_jobs import get_job_store
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_workflow import *
from ..contracts.unified_research_runtime import UnifiedResearchRuntimeExecutionRequest, UnifiedResearchRuntimePlan, UnifiedResearchStagePayloads
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None

SAFE_EXECUTABLE={"retrieval","research-intelligence","argument-synthesis","statistical-analysis","visual-research","project-state"}
TERMINAL={"completed","failed","cancelled"}

def _json(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
def _sha(v:Any)->str:return hashlib.sha256(_json(v).encode()).hexdigest()
def _now()->str:return datetime.now(timezone.utc).isoformat()

class ResearchWorkflowStore:
    def __init__(self,sqlite_path:Path|None=None):
        self.backend="postgres" if settings.database_backend=="postgres" else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_workflows.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema);self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres workflow storage requires psycopg.")
            self._migrate_postgres()
        else:self.sqlite_path.parent.mkdir(parents=True,exist_ok=True);self._migrate_sqlite()
    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None);c.row_factory=sqlite3.Row;c.execute("PRAGMA journal_mode=WAL");c.execute("PRAGMA busy_timeout=30000")
        try:yield c
        finally:c.close()
    @contextmanager
    def _postgres(self,migration=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url;c=psycopg.connect(url,autocommit=False,row_factory=dict_row);c.execute(f'SET search_path TO "{self.database_schema}"')
        try:yield c
        finally:c.close()
    def _migrate_sqlite(self):
        with self._lock,self._sqlite() as c:c.executescript("""
CREATE TABLE IF NOT EXISTS research_workflows(workflow_id TEXT PRIMARY KEY,state TEXT NOT NULL,run_id TEXT NOT NULL UNIQUE,core_project_id TEXT NOT NULL,local_project_id TEXT NOT NULL DEFAULT '',record_json TEXT NOT NULL,workflow_fingerprint TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL,completed_utc TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_research_workflows_state ON research_workflows(state,updated_utc);
CREATE TABLE IF NOT EXISTS research_workflow_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,workflow_id TEXT NOT NULL,event_type TEXT NOT NULL,stage TEXT NOT NULL DEFAULT '',actor_ref TEXT NOT NULL DEFAULT '',message TEXT NOT NULL DEFAULT '',payload_json TEXT NOT NULL DEFAULT '{}',created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_workflow_checkpoints(checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,workflow_id TEXT NOT NULL,checkpoint_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_workflows(workflow_id TEXT PRIMARY KEY,state TEXT NOT NULL,run_id TEXT NOT NULL UNIQUE,core_project_id TEXT NOT NULL,local_project_id TEXT NOT NULL DEFAULT '',record JSONB NOT NULL,workflow_fingerprint TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),completed_utc TIMESTAMPTZ);""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_workflow_events(event_id BIGSERIAL PRIMARY KEY,workflow_id TEXT NOT NULL REFERENCES sc_rl_research_workflows(workflow_id) ON DELETE CASCADE,event_type TEXT NOT NULL,stage TEXT NOT NULL DEFAULT '',actor_ref TEXT NOT NULL DEFAULT '',message TEXT NOT NULL DEFAULT '',payload JSONB NOT NULL DEFAULT '{}'::jsonb,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_workflow_checkpoints(checkpoint_id BIGSERIAL PRIMARY KEY,workflow_id TEXT NOT NULL REFERENCES sc_rl_research_workflows(workflow_id) ON DELETE CASCADE,checkpoint_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());""");c.commit()
    def _event(self,wid,event_type,stage="",actor_ref="",message="",payload=None):
        payload=payload or {};now=_now()
        if self.backend=="postgres":
            with self._postgres() as c:c.execute("INSERT INTO sc_rl_research_workflow_events(workflow_id,event_type,stage,actor_ref,message,payload,created_utc) VALUES(%s,%s,%s,%s,%s,%s,%s)",(wid,event_type,stage,actor_ref,message[:2000],Jsonb(payload),now));c.commit()
        else:
            with self._lock,self._sqlite() as c:c.execute("INSERT INTO research_workflow_events(workflow_id,event_type,stage,actor_ref,message,payload_json,created_utc) VALUES(?,?,?,?,?,?,?)",(wid,event_type,stage,actor_ref,message[:2000],_json(payload),now))
    def _save(self,r):
        r=dict(r);r["updated_utc"]=_now();r["workflow_fingerprint"]=_sha({k:v for k,v in r.items() if k not in {"workflow_fingerprint","updated_utc"}})
        if self.backend=="postgres":
            with self._postgres() as c:c.execute("UPDATE sc_rl_research_workflows SET state=%s,record=%s,workflow_fingerprint=%s,updated_utc=%s,completed_utc=%s WHERE workflow_id=%s",(r["state"],Jsonb(r),r["workflow_fingerprint"],r["updated_utc"],r.get("completed_utc") or None,r["workflow_id"]));c.commit()
        else:
            with self._lock,self._sqlite() as c:c.execute("UPDATE research_workflows SET state=?,record_json=?,workflow_fingerprint=?,updated_utc=?,completed_utc=? WHERE workflow_id=?",(r["state"],_json(r),r["workflow_fingerprint"],r["updated_utc"],r.get("completed_utc","") or "",r["workflow_id"]))
        return r
    def find_by_run_id(self,run_id):
        if self.backend=="postgres":
            with self._postgres() as c:row=c.execute("SELECT record FROM sc_rl_research_workflows WHERE run_id=%s",(run_id,)).fetchone();c.commit()
            return dict(row["record"]) if row else None
        with self._lock,self._sqlite() as c:row=c.execute("SELECT record_json FROM research_workflows WHERE run_id=?",(run_id,)).fetchone()
        return json.loads(row["record_json"]) if row else None
    def create(self,request:ResearchWorkflowCreateRequest):
        old=self.find_by_run_id(request.plan.run_id)
        if old:return old,True
        now=_now();wid="rl-workflow-"+uuid.uuid4().hex
        stages=[{"stage":x["stage"],"sequence":x["sequence"],"dependencies":list(x.get("depends_on") or []),"gate":x.get("gate"),"owner":x.get("owner",""),"mode":x.get("mode",""),"status":"pending","approval":None,"job_id":None,"attempts":0,"result_hash":None,"message":""} for x in request.plan.stages]
        r={"schema":RESEARCH_WORKFLOW_SCHEMA,"release":settings.release_version,"workflow_id":wid,"state":"draft","run_id":request.plan.run_id,"core_project_id":request.plan.core_project_id,"local_project_id":request.plan.local_project_id,"plan":request.plan.model_dump(mode="json",exclude_none=True),"payloads":request.payloads.model_dump(mode="json",exclude_none=True),"stages":stages,"auto_schedule_safe_stages":request.auto_schedule_safe_stages,"max_parallel_stages":request.max_parallel_stages,"max_attempts_per_stage":request.max_attempts_per_stage,"metadata":request.metadata,"created_utc":now,"updated_utc":now,"completed_utc":"","workflow_fingerprint":""};r["workflow_fingerprint"]=_sha(r)
        if self.backend=="postgres":
            with self._postgres() as c:c.execute("INSERT INTO sc_rl_research_workflows(workflow_id,state,run_id,core_project_id,local_project_id,record,workflow_fingerprint,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(wid,"draft",r["run_id"],r["core_project_id"],r.get("local_project_id") or "",Jsonb(r),r["workflow_fingerprint"],now,now));c.commit()
        else:
            with self._lock,self._sqlite() as c:c.execute("INSERT INTO research_workflows(workflow_id,state,run_id,core_project_id,local_project_id,record_json,workflow_fingerprint,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?)",(wid,"draft",r["run_id"],r["core_project_id"],r.get("local_project_id") or "",_json(r),r["workflow_fingerprint"],now,now))
        self._event(wid,"created",payload={"run_id":r["run_id"]});self.checkpoint(wid,"created");return r,False
    def get(self,wid):
        if self.backend=="postgres":
            with self._postgres() as c:row=c.execute("SELECT record FROM sc_rl_research_workflows WHERE workflow_id=%s",(wid,)).fetchone();c.commit()
            if not row:raise KeyError(wid)
            return dict(row["record"])
        with self._lock,self._sqlite() as c:row=c.execute("SELECT record_json FROM research_workflows WHERE workflow_id=?",(wid,)).fetchone()
        if not row:raise KeyError(wid)
        return json.loads(row["record_json"])
    def list(self,state="",limit=100):
        limit=max(1,min(500,int(limit)))
        if self.backend=="postgres":
            q="SELECT record FROM sc_rl_research_workflows";args=[]
            if state:q+=" WHERE state=%s";args.append(state)
            q+=" ORDER BY updated_utc DESC LIMIT %s";args.append(limit)
            with self._postgres() as c:rows=c.execute(q,tuple(args)).fetchall();c.commit()
            return [dict(x["record"]) for x in rows]
        q="SELECT record_json FROM research_workflows";args=[]
        if state:q+=" WHERE state=?";args.append(state)
        q+=" ORDER BY updated_utc DESC LIMIT ?";args.append(limit)
        with self._lock,self._sqlite() as c:rows=c.execute(q,tuple(args)).fetchall()
        return [json.loads(x["record_json"]) for x in rows]
    def control(self,wid,request:ResearchWorkflowControlRequest):
        r=self.get(wid);a=request.action
        if a=="start":
            if r["state"]!="draft":raise ValueError("Only draft workflows can be started.")
            r["state"]="running"
        elif a=="pause":
            if r["state"] not in {"running","blocked"}:raise ValueError("Only running or blocked workflows can be paused.")
            r["state"]="paused"
        elif a=="resume":
            if r["state"]!="paused":raise ValueError("Only paused workflows can be resumed.")
            r["state"]="running"
        elif a=="cancel":
            if r["state"] in TERMINAL:return r
            r["state"]="cancelled";r["completed_utc"]=_now();js=get_job_store()
            for s in r["stages"]:
                if s.get("job_id"):
                    try:js.cancel(s["job_id"])
                    except Exception:pass
                if s["status"] not in {"completed","failed"}:s["status"]="cancelled"
        elif a=="retry-failed":
            for s in r["stages"]:
                if s["status"]=="failed":s.update(status="pending",job_id=None,message="manual retry")
            r["state"]="running"
        self._event(wid,"control",actor_ref=request.actor_ref,message=f"{a}: {request.reason}");return self._save(r)
    def approve(self,wid,request:ResearchWorkflowApprovalRequest):
        r=self.get(wid);s=next((x for x in r["stages"] if x["stage"]==request.stage),None)
        if not s:raise KeyError(request.stage)
        s["approval"]={"decision":request.decision,"reviewer_ref":request.reviewer_ref,"note":request.note,"reviewed_utc":_now()}
        if request.decision=="approved" and s["status"]=="awaiting-approval":s["status"]="pending"
        if request.decision=="rejected":s["status"]="blocked";s["message"]="review rejected"
        self._event(wid,"approval",stage=request.stage,actor_ref=request.reviewer_ref,message=request.note,payload={"decision":request.decision});return self._save(r)
    def checkpoint(self,wid,reason="manual"):
        r=self.get(wid);payload={"workflow_id":wid,"state":r["state"],"stages":[{"stage":s["stage"],"status":s["status"],"job_id":s.get("job_id"),"result_hash":s.get("result_hash")} for s in r["stages"]],"workflow_fingerprint":r["workflow_fingerprint"],"reason":reason};h=_sha(payload);now=_now()
        if self.backend=="postgres":
            with self._postgres() as c:c.execute("INSERT INTO sc_rl_research_workflow_checkpoints(workflow_id,checkpoint_hash,record,created_utc) VALUES(%s,%s,%s,%s)",(wid,h,Jsonb(payload),now));c.commit()
        else:
            with self._lock,self._sqlite() as c:c.execute("INSERT INTO research_workflow_checkpoints(workflow_id,checkpoint_hash,record_json,created_utc) VALUES(?,?,?,?)",(wid,h,_json(payload),now))
        self._event(wid,"checkpoint",message=reason,payload={"checkpoint_hash":h});return {"schema":RESEARCH_WORKFLOW_CHECKPOINT_SCHEMA,"checkpoint_hash":h,"created_utc":now,"record":payload}
    def checkpoints(self,wid,limit=100):
        self.get(wid);limit=max(1,min(500,int(limit)))
        if self.backend=="postgres":
            with self._postgres() as c:rows=c.execute("SELECT checkpoint_id,checkpoint_hash,record,created_utc FROM sc_rl_research_workflow_checkpoints WHERE workflow_id=%s ORDER BY checkpoint_id DESC LIMIT %s",(wid,limit)).fetchall();c.commit()
            return [{"schema":RESEARCH_WORKFLOW_CHECKPOINT_SCHEMA,**dict(x)} for x in rows]
        with self._lock,self._sqlite() as c:rows=c.execute("SELECT * FROM research_workflow_checkpoints WHERE workflow_id=? ORDER BY checkpoint_id DESC LIMIT ?",(wid,limit)).fetchall()
        return [{"schema":RESEARCH_WORKFLOW_CHECKPOINT_SCHEMA,"checkpoint_id":x["checkpoint_id"],"checkpoint_hash":x["checkpoint_hash"],"record":json.loads(x["record_json"]),"created_utc":x["created_utc"]} for x in rows]
    def events(self,wid,limit=200):
        self.get(wid);limit=max(1,min(1000,int(limit)))
        if self.backend=="postgres":
            with self._postgres() as c:rows=c.execute("SELECT * FROM sc_rl_research_workflow_events WHERE workflow_id=%s ORDER BY event_id DESC LIMIT %s",(wid,limit)).fetchall();c.commit()
            return [{"schema":RESEARCH_WORKFLOW_EVENT_SCHEMA,**dict(x)} for x in rows]
        with self._lock,self._sqlite() as c:rows=c.execute("SELECT * FROM research_workflow_events WHERE workflow_id=? ORDER BY event_id DESC LIMIT ?",(wid,limit)).fetchall()
        return [{"schema":RESEARCH_WORKFLOW_EVENT_SCHEMA,"event_id":x["event_id"],"event_type":x["event_type"],"stage":x["stage"],"actor_ref":x["actor_ref"],"message":x["message"],"payload":json.loads(x["payload_json"]),"created_utc":x["created_utc"]} for x in rows]
    def advance(self,wid,request:ResearchWorkflowAdvanceRequest):
        r=self.get(wid)
        if r["state"]=="draft":raise ValueError("Workflow must be started before it can advance.")
        if r["state"] in {"paused","cancelled","completed"}:return {"schema":RESEARCH_WORKFLOW_SCHEMA,"release":settings.release_version,"workflow":r,"scheduled_jobs":[],"changed":False,"storage_backend":self.backend}
        js=get_job_store();changed=False;scheduled=[]
        for s in r["stages"]:
            if not s.get("job_id"):continue
            try:j=js.get(s["job_id"])
            except KeyError:s["status"]="failed";s["message"]="durable job missing";changed=True;continue
            ns={"queued":"queued","retry_wait":"queued","running":"running","succeeded":"completed","failed":"failed","cancelled":"cancelled"}.get(j["state"],s["status"])
            if ns!=s["status"]:s["status"]=ns;changed=True
            s["attempts"]=int(j.get("attempts",0))
            if j["state"]=="succeeded":s["result_hash"]=_sha(j.get("result") or {});s["message"]="durable job succeeded"
            elif j["state"]=="failed":s["message"]=j.get("error","")[:1000]
        by={x["stage"]:x for x in r["stages"]};active=sum(x["status"] in {"queued","running"} for x in r["stages"]);allow=max(0,min(request.max_new_jobs,int(r["max_parallel_stages"])-active))
        for s in sorted(r["stages"],key=lambda x:x["sequence"]):
            if s["status"] not in {"pending","awaiting-approval"}:continue
            if any(by.get(d,{}).get("status")!="completed" for d in s["dependencies"] if d in by):continue
            if s.get("gate") and (s.get("approval") or {}).get("decision")!="approved":s["status"]="awaiting-approval";s["message"]="human approval required";changed=True;continue
            if s["stage"] not in SAFE_EXECUTABLE:s["status"]="awaiting-external";s["message"]="explicit external/API action required";changed=True;continue
            if not request.schedule_jobs or not r["auto_schedule_safe_stages"] or allow<=0:continue
            plan=UnifiedResearchRuntimePlan.model_validate(r["plan"]);payloads=UnifiedResearchStagePayloads.model_validate(r.get("payloads") or {})
            er=UnifiedResearchRuntimeExecutionRequest(plan=plan,payloads=payloads,execute_stages=[s["stage"]])
            job,replayed=js.enqueue("unified-research-runtime",er.model_dump(mode="json",exclude_none=True),max_attempts=r["max_attempts_per_stage"],idempotency_key=f"workflow:{wid}:{s['stage']}:{plan.reproducibility.get('plan_hash','')}")
            s["job_id"]=job["job_id"];s["status"]="completed" if job["state"]=="succeeded" else "queued";s["message"]="replayed durable job" if replayed else "durable job queued";scheduled.append(job["job_id"]);allow-=1;changed=True;self._event(wid,"stage-job-enqueued",stage=s["stage"],actor_ref=request.actor_ref,payload={"job_id":job["job_id"],"replayed":replayed})
        statuses={x["status"] for x in r["stages"]}
        if statuses and all(x=="completed" for x in statuses):r["state"]="completed";r["completed_utc"]=_now();changed=True
        elif "failed" in statuses:r["state"]="failed"
        elif statuses & {"queued","running","pending"}:r["state"]="running"
        elif statuses & {"awaiting-approval","awaiting-external","blocked"}:r["state"]="blocked"
        if changed:r=self._save(r);self._event(wid,"advanced",actor_ref=request.actor_ref,payload={"scheduled_jobs":scheduled});self.checkpoint(wid,"advance")
        return {"schema":RESEARCH_WORKFLOW_SCHEMA,"release":settings.release_version,"workflow":r,"scheduled_jobs":scheduled,"changed":changed,"storage_backend":self.backend}

_store=None;_store_lock=threading.Lock()
def get_research_workflow_store():
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:_store=ResearchWorkflowStore()
    return _store

def capabilities():
    s=get_research_workflow_store();return {"schema":RESEARCH_WORKFLOW_SCHEMA,"release":settings.release_version,"storage_backend":s.backend,"durable":True,"resumable":True,"dependency_aware":True,"checkpointed":True,"auditable_events":True,"pause_resume_cancel":True,"manual_retry":True,"human_approvals":True,"safe_stage_jobs_use_unified_runtime":True,"automatic_core_writes":False,"automatic_truth_promotion":False,"maximum_parallel_stages":8}
