from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib,json,sqlite3,threading
from pathlib import Path
from typing import Any,Iterator,Callable

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.integrated_computational_research_scientist_environment import *

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256(_json(v).encode()).hexdigest()
def _now(): return datetime.now(timezone.utc).isoformat()
def _id(prefix,v): return prefix+_sha(v)[:32]

class IntegratedComputationalResearchScientistEnvironmentStore:
    def __init__(self,sqlite_path:Path|None=None,unified_environment_resolver:Callable[[str],dict[str,Any]]|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"integrated_computational_research_scientist_environment.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        self.unified_environment_resolver=unified_environment_resolver
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres scientist-environment storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    def _resolve_unified_environment(self,ref):
        resolver=self.unified_environment_resolver
        if resolver is None:
            from .unified_scholarly_ai_environment import get_unified_scholarly_ai_environment_store
            resolver=get_unified_scholarly_ai_environment_store().dossier
        try: dossier=resolver(ref)
        except Exception as exc: raise ValueError(f"unified research environment is not available: {ref}") from exc
        return dossier

    @contextmanager
    def _sqlite(self):
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self,migration=False):
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self):
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS scientist_environments(scientist_environment_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scientist_environment_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,scientist_environment_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scientist_environment_snapshots(snapshot_id TEXT PRIMARY KEY,scientist_environment_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_scientist_environments(scientist_environment_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_scientist_environment_events(event_id BIGSERIAL PRIMARY KEY,scientist_environment_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_scientist_environment_events_env ON sc_rl_scientist_environment_events(scientist_environment_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_scientist_environment_snapshots(snapshot_id TEXT PRIMARY KEY,scientist_environment_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]:
                c.execute(ddl)
            c.commit()

    def _event(self,eid,typ,actor,payload):
        created=_now(); h=_sha({"scientist_environment_id":eid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_scientist_environment_events(scientist_environment_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(eid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute("INSERT INTO scientist_environment_events(scientist_environment_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(eid,typ,actor,_json(payload),h,created))

    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_scientist_environments(scientist_environment_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(scientist_environment_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["scientist_environment_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute("INSERT OR REPLACE INTO scientist_environments(scientist_environment_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["scientist_environment_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec

    def get(self,eid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_scientist_environments WHERE scientist_environment_id=%s",(eid,)).fetchone()
            if not row: raise ValueError("Scientist environment not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM scientist_environments WHERE scientist_environment_id=?",(eid,)).fetchone()
        if not row: raise ValueError("Scientist environment not found.")
        return json.loads(row["record_json"])

    def create(self,req):
        body=req.model_dump(); actor=body.pop("actor_ref")
        dossier=self._resolve_unified_environment(body["unified_environment_ref"])
        unified_hash=str(((dossier.get("environment") or {}).get("record_hash")) or dossier.get("record_hash") or "")
        seed={**body,"unified_environment_hash":unified_hash}; eid=_id("scientist-",seed)
        try:return self.get(eid)
        except ValueError:pass
        rec={
            "schema":SCIENTIST_ENVIRONMENT_SCHEMA,
            "scientist_environment_id":eid,
            **body,
            "unified_environment_hash":unified_hash,
            "stages":[],
            "work_packages":[],
            "runtime_handoffs":[],
            "execution_receipts":[],
            "interpretations":[],
            "checkpoints":[],
            "decisions":[],
            "state":{"value":"draft","actor_ref":actor,"note":"","updated_utc":_now()},
            "created_utc":_now(),
            "updated_utc":_now(),
            "governance":{
                "source_component_authority_preserved":True,
                "specialist_runtimes_own_execution":True,
                "execution_receipts_are_observations_not_scientific_verdicts":True,
                "interpretations_are_human_authored":True,
                "checkpoints_require_human_decision":True,
                "platform_core_governance_remains_external":True,
                "automatic_execution":False,
                "automatic_model_selection":False,
                "automatic_causal_inference":False,
                "automatic_scientific_validity_verdict":False,
                "automatic_scholarly_judgment":False,
                "automatic_truth_promotion":False,
            },
        }
        self._save(rec); self._event(eid,"scientist-environment.created",actor,{"unified_environment_ref":body["unified_environment_ref"]}); return self.get(eid)

    def _append(self,eid,key,idkey,prefix,body,event,extra=None):
        rec=self.get(eid); actor=body.pop("actor_ref"); oid=_id(prefix,body)
        item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x[idkey]==oid for x in rec[key]):
            rec[key].append(item); self._save(rec); self._event(eid,event,actor,{idkey:oid})
        return self.get(eid)

    def add_stage(self,eid,req):
        return self._append(eid,"stages","stage_id","stage-",req.model_dump(),"stage.added",{"decision":"pending","status":"open"})

    def add_work_package(self,eid,req):
        rec=self.get(eid)
        if req.stage_id not in {x["stage_id"] for x in rec["stages"]}: raise ValueError("stage_id is not registered.")
        return self._append(eid,"work_packages","work_package_id","work-",req.model_dump(),"work-package.added",{"decision":"pending","execution_state":"not-started"})

    def add_runtime_handoff(self,eid,req):
        rec=self.get(eid)
        if req.work_package_id not in {x["work_package_id"] for x in rec["work_packages"]}: raise ValueError("work_package_id is not registered.")
        return self._append(eid,"runtime_handoffs","runtime_handoff_id","handoff-",req.model_dump(),"runtime-handoff.added",{"decision":"pending","execution_performed":False})

    def add_execution_receipt(self,eid,req):
        rec=self.get(eid); handoff=next((x for x in rec["runtime_handoffs"] if x["runtime_handoff_id"]==req.runtime_handoff_id),None)
        if handoff is None: raise ValueError("runtime_handoff_id is not registered.")
        if handoff.get("decision")!="approved": raise ValueError("runtime handoff requires explicit human approval before accepting an execution receipt.")
        out=self._append(eid,"execution_receipts","execution_receipt_id","execution-",req.model_dump(),"execution-receipt.added",{"receipt_is_observation_not_scientific_verdict":True})
        rec=self.get(eid)
        for wp in rec["work_packages"]:
            if wp["work_package_id"]==handoff["work_package_id"]:
                wp["execution_state"]=req.status; wp["execution_updated_utc"]=_now()
        self._save(rec)
        return self.get(eid)

    def add_interpretation(self,eid,req):
        rec=self.get(eid)
        if req.work_package_id not in {x["work_package_id"] for x in rec["work_packages"]}: raise ValueError("work_package_id is not registered.")
        known={x["execution_receipt_id"] for x in rec["execution_receipts"]}
        unknown=[x for x in req.execution_receipt_ids if x not in known]
        if unknown: raise ValueError(f"unknown execution_receipt_ids: {unknown}")
        return self._append(eid,"interpretations","interpretation_id","interpretation-",req.model_dump(),"interpretation.added",{"human_authored":True,"decision":"pending","not_scientific_validity_verdict":True})

    def add_checkpoint(self,eid,req):
        rec=self.get(eid)
        if req.stage_id not in {x["stage_id"] for x in rec["stages"]}: raise ValueError("stage_id is not registered.")
        return self._append(eid,"checkpoints","checkpoint_id","checkpoint-",req.model_dump(),"checkpoint.added",{"status":"open","decision_actor_ref":"","decision_rationale":""})

    def decide_checkpoint(self,eid,req):
        rec=self.get(eid); found=False
        for cp in rec["checkpoints"]:
            if cp["checkpoint_id"]==req.checkpoint_id:
                cp.update({"status":req.status,"decision_actor_ref":req.actor_ref,"decision_rationale":req.rationale,"decision_updated_utc":_now()}); found=True; break
        if not found: raise ValueError("checkpoint_id is not registered.")
        self._save(rec); self._event(eid,"checkpoint.decided",req.actor_ref,{"checkpoint_id":req.checkpoint_id,"status":req.status}); return self.get(eid)

    def decide(self,eid,req):
        rec=self.get(eid)
        mapping={"stage":("stages","stage_id"),"work-package":("work_packages","work_package_id"),"runtime-handoff":("runtime_handoffs","runtime_handoff_id"),"interpretation":("interpretations","interpretation_id")}
        if req.object_type=="dossier":
            expected="scientist-dossier-"+eid
            if req.object_id!=expected: raise ValueError("dossier object_id must match the scientist dossier id.")
        else:
            key,idkey=mapping[req.object_type]; obj=next((x for x in rec[key] if x[idkey]==req.object_id),None)
            if obj is None: raise ValueError("decision object is not registered.")
            obj.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decision_updated_utc":_now()})
        rec["decisions"].append({"decision_id":_id("decision-",req.model_dump()),**req.model_dump(),"created_utc":_now()})
        self._save(rec); self._event(eid,"human-decision.recorded",req.actor_ref,req.model_dump()); return self.get(eid)

    def set_state(self,eid,req):
        rec=self.get(eid); rec["state"]={"value":req.state,"actor_ref":req.actor_ref,"note":req.note,"updated_utc":_now()}
        self._save(rec); self._event(eid,"scientist-environment.state",req.actor_ref,{"state":req.state}); return self.get(eid)

    def lifecycle_map(self,eid):
        rec=self.get(eid); rows=[]
        for stage in rec["stages"]:
            packages=[x for x in rec["work_packages"] if x["stage_id"]==stage["stage_id"]]
            cps=[x for x in rec["checkpoints"] if x["stage_id"]==stage["stage_id"]]
            rows.append({"stage_id":stage["stage_id"],"stage_type":stage["stage_type"],"label":stage["label"],"status":stage["status"],"work_package_count":len(packages),"checkpoint_count":len(cps),"approved_checkpoint_count":sum(1 for x in cps if x["status"]=="approved")})
        return {"schema":SCIENTIST_ENVIRONMENT_SCHEMA,"scientist_environment_id":eid,"rows":rows,"governance":{"lifecycle_map_is_process_state_not_scientific_quality_score":True}}

    def workbench(self,eid):
        rec=self.get(eid); receipts_by_handoff={}
        for r in rec["execution_receipts"]: receipts_by_handoff.setdefault(r["runtime_handoff_id"],[]).append(r)
        rows=[]
        for wp in rec["work_packages"]:
            handoffs=[x for x in rec["runtime_handoffs"] if x["work_package_id"]==wp["work_package_id"]]
            interpretations=[x for x in rec["interpretations"] if x["work_package_id"]==wp["work_package_id"]]
            rows.append({"work_package":wp,"runtime_handoffs":[{**h,"execution_receipts":receipts_by_handoff.get(h["runtime_handoff_id"],[])} for h in handoffs],"interpretations":interpretations})
        return {"schema":SCIENTIST_ENVIRONMENT_SCHEMA,"scientist_environment_id":eid,"rows":rows,"governance":{"execution_and_interpretation_remain_separate":True}}

    def runtime_handoffs(self,eid):
        rec=self.get(eid); packets=[]
        for h in rec["runtime_handoffs"]:
            if h.get("decision")=="approved":
                wp=next((x for x in rec["work_packages"] if x["work_package_id"]==h["work_package_id"]),{})
                packets.append({"schema":"sc-research-librarian-computational-scientist-runtime-handoff/1.0","scientist_environment_id":eid,"runtime_handoff_id":h["runtime_handoff_id"],"runtime_target":h["runtime_target"],"work_package_id":h["work_package_id"],"research_task":wp.get("research_task",""),"input_refs":wp.get("input_refs",[]),"execution_spec":h["execution_spec"],"expected_artifacts":h["expected_artifacts"],"execution_performed":False,"scientific_judgment_not_delegated":True})
        return {"schema":SCIENTIST_ENVIRONMENT_SCHEMA,"scientist_environment_id":eid,"packets":packets}

    def provenance_map(self,eid):
        rec=self.get(eid)
        return {"schema":SCIENTIST_ENVIRONMENT_SCHEMA,"scientist_environment_id":eid,"unified_environment_ref":rec["unified_environment_ref"],"unified_environment_hash":rec["unified_environment_hash"],"work_package_inputs":[{"work_package_id":x["work_package_id"],"input_refs":x["input_refs"]} for x in rec["work_packages"]],"execution_lineage":[{"execution_receipt_id":x["execution_receipt_id"],"runtime_handoff_id":x["runtime_handoff_id"],"execution_ref":x["execution_ref"],"runtime_version":x["runtime_version"],"environment_ref":x["environment_ref"],"artifact_refs":x["artifact_refs"]} for x in rec["execution_receipts"]],"interpretation_lineage":[{"interpretation_id":x["interpretation_id"],"work_package_id":x["work_package_id"],"execution_receipt_ids":x["execution_receipt_ids"],"evidence_refs":x["evidence_refs"]} for x in rec["interpretations"]]}

    def readiness(self,eid):
        rec=self.get(eid)
        dims={
            "unified_environment_bound":bool(rec["unified_environment_ref"]),
            "lifecycle_stage_present":bool(rec["stages"]),
            "work_package_present":bool(rec["work_packages"]),
            "all_approved_handoffs_have_receipts":all(any(r["runtime_handoff_id"]==h["runtime_handoff_id"] for r in rec["execution_receipts"]) for h in rec["runtime_handoffs"] if h.get("decision")=="approved"),
            "all_completed_work_has_human_interpretation":all(any(i["work_package_id"]==w["work_package_id"] for i in rec["interpretations"]) for w in rec["work_packages"] if w.get("execution_state")=="completed"),
            "no_rejected_checkpoint":not any(x["status"]=="rejected" for x in rec["checkpoints"]),
        }
        blockers=[k.replace("_","-") for k in ["unified_environment_bound","lifecycle_stage_present","work_package_present","all_approved_handoffs_have_receipts","all_completed_work_has_human_interpretation","no_rejected_checkpoint"] if not dims[k]]
        return {"schema":SCIENTIST_ENVIRONMENT_SCHEMA,"scientist_environment_id":eid,"ready_for_reproducible_dossier":not blockers,"dimensions":dims,"blockers":blockers,"governance":{"readiness_is_structural_and_provenance_completeness_not_scientific_validity":True}}

    def dossier(self,eid):
        rec=self.get(eid)
        unified=self._resolve_unified_environment(rec["unified_environment_ref"])
        return {
            "schema":"sc-research-librarian-integrated-computational-research-scientist-dossier/1.0",
            "dossier_id":"scientist-dossier-"+eid,
            "scientist_environment_id":eid,
            "environment":{"title":rec["title"],"project_ref":rec["project_ref"],"research_question":rec["research_question"],"objective":rec["objective"],"record_hash":rec["record_hash"]},
            "unified_research_environment":unified,
            "lifecycle_map":self.lifecycle_map(eid),
            "scientist_workbench":self.workbench(eid),
            "runtime_handoffs":self.runtime_handoffs(eid),
            "provenance_map":self.provenance_map(eid),
            "readiness":self.readiness(eid),
            "checkpoints":rec["checkpoints"],
            "governance":{"assembled_environment_not_new_source_of_truth":True,"component_authority_preserved":True,"human_scholarly_judgment_required":True,"specialist_runtime_execution_preserved":True,"platform_core_governance_preserved":True,"automatic_truth_promotion":False},
        }

    def core_candidate(self,eid):
        rec=self.get(eid)
        return {"schema":"sc-research-librarian-integrated-computational-research-scientist-core-candidate/1.0","scientist_environment_id":eid,"record_hash":rec["record_hash"],"unified_environment_ref":rec["unified_environment_ref"],"stages":rec["stages"],"work_packages":rec["work_packages"],"execution_receipts":rec["execution_receipts"],"interpretations":rec["interpretations"],"checkpoints":rec["checkpoints"],"human_review_required":True,"scientific_validity_not_certified":True,"truth_promoted":False}

    def freeze_snapshot(self,req):
        dossier=self.dossier(req.scientist_environment_id)
        payload={"schema":SCIENTIST_ENVIRONMENT_SNAPSHOT_SCHEMA,"scientist_environment_id":req.scientist_environment_id,"dossier":dossier,"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_research_environment_record_not_truth_certification":True}}
        h=_sha(payload); sid="scientistsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_scientist_environment_snapshots(snapshot_id,scientist_environment_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.scientist_environment_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute("INSERT OR IGNORE INTO scientist_environment_snapshots(snapshot_id,scientist_environment_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.scientist_environment_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.scientist_environment_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {
        "schema":SCIENTIST_ENVIRONMENT_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.0",
        "durable":True,
        "unified_research_environment_binding":True,
        "research_lifecycle_stages":True,
        "computational_work_packages":True,
        "human_approved_runtime_handoffs":True,
        "execution_receipts":True,
        "human_interpretations":True,
        "human_checkpoints":True,
        "provenance_map":True,
        "reproducible_scientist_dossier":True,
        "source_component_authority_preserved":True,
        "specialist_runtimes_own_execution":True,
        "platform_core_governance_remains_external":True,
        "automatic_execution":False,
        "automatic_model_selection":False,
        "automatic_causal_inference":False,
        "automatic_scientific_validity_verdict":False,
        "automatic_scholarly_judgment":False,
        "automatic_truth_promotion":False,
    }

_store=None
def get_integrated_computational_research_scientist_environment_store():
    global _store
    if _store is None:_store=IntegratedComputationalResearchScientistEnvironmentStore()
    return _store
