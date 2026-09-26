from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.dataset_discovery_data_fitness import *
from .research_gap_novelty_intelligence import get_research_gap_novelty_intelligence_store
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256(_json(v).encode()).hexdigest()
def _now(): return datetime.now(timezone.utc).isoformat()
def _uniq(v): return list(dict.fromkeys(str(x).strip() for x in v if str(x).strip()))
def _id(p,v): return p+_sha(v)[:32]

class DatasetDiscoveryDataFitnessStore:
    def __init__(self,sqlite_path:Path|None=None,gap_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"dataset_discovery_data_fitness.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.gap_store=gap_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres dataset fitness storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _gaps(self): return self.gap_store or get_research_gap_novelty_intelligence_store()
    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()
    @contextmanager
    def _postgres(self,migration=False):
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()
    def _migrate_sqlite(self):
        with self._lock,self._sqlite() as c: c.executescript("""
CREATE TABLE IF NOT EXISTS dataset_fitness_projects(data_fitness_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dataset_fitness_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,data_fitness_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dataset_fitness_snapshots(snapshot_id TEXT PRIMARY KEY,data_fitness_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_dataset_fitness_projects(data_fitness_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_dataset_fitness_events(event_id BIGSERIAL PRIMARY KEY,data_fitness_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_dataset_fitness_events_project ON sc_rl_dataset_fitness_events(data_fitness_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_dataset_fitness_snapshots(snapshot_id TEXT PRIMARY KEY,data_fitness_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,did,typ,actor,payload):
        created=_now(); h=_sha({"data_fitness_id":did,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_dataset_fitness_events(data_fitness_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(did,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO dataset_fitness_events(data_fitness_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(did,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_dataset_fitness_projects(data_fitness_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(data_fitness_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["data_fitness_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO dataset_fitness_projects(data_fitness_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["data_fitness_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,did):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_dataset_fitness_projects WHERE data_fitness_id=%s",(did,)).fetchone()
            if not row: raise ValueError("Dataset fitness project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM dataset_fitness_projects WHERE data_fitness_id=?",(did,)).fetchone()
        if not row: raise ValueError("Dataset fitness project not found.")
        return json.loads(row["record_json"])
    def create(self,req:DatasetFitnessCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref"); upstream={}
        if body.get("gap_novelty_id"):
            upstream=self._gaps().get(body["gap_novelty_id"]); body["research_question"]=body.get("research_question") or upstream.get("research_question",""); body["core_project_id"]=body.get("core_project_id") or upstream.get("core_project_id","")
            known={x.get("opportunity_id") for x in upstream.get("research_opportunities",[])}; missing=[x for x in body["research_opportunity_ids"] if x not in known]
            if missing: raise ValueError("One or more research_opportunity_ids are not present in the bound gap/novelty project.")
        body["research_opportunity_ids"]=_uniq(body["research_opportunity_ids"]); did=_id("datafit-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(did)
        except ValueError: pass
        rec={"schema":DATASET_DISCOVERY_FITNESS_SCHEMA,"data_fitness_id":did,**body,"gap_novelty_fingerprint":upstream.get("record_hash","") if upstream else "","data_requirements":[],"dataset_candidates":[],"variables":[],"fitness_assessments":[],"review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),"governance":{"dataset_discovery_is_candidate_generation_not_endorsement":True,"human_fitness_decision_required":True,"fitness_is_question_specific_not_global_quality":True,"metadata_absence_is_not_proof_of_data_absence":True,"license_and_access_require_human_verification":True,"automatic_dataset_suitability":False,"automatic_quality_certification":False,"automatic_variable_semantics_inference":False,"automatic_truth_promotion":False,"platform_core_remains_research_object_authority":True}}
        self._save(rec); self._event(did,"dataset-fitness.created",actor,{"gap_novelty_id":body.get("gap_novelty_id","")}); return self.get(did)
    def add_requirement(self,did,req:DataRequirementAddRequest):
        rec=self.get(did); body=req.model_dump(); actor=body.pop("actor_ref"); body["required_variables"]=_uniq(body["required_variables"]); body["opportunity_ids"]=_uniq(body["opportunity_ids"])
        known=set(rec.get("research_opportunity_ids",[])); missing=[x for x in body["opportunity_ids"] if x not in known]
        if missing: raise ValueError("Data requirement references an unknown research opportunity.")
        rid=_id("dreq-",body); item={"requirement_id":rid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["requirement_id"]==rid for x in rec["data_requirements"]): rec["data_requirements"].append(item); self._save(rec); self._event(did,"data-requirement.added",actor,{"requirement_id":rid})
        return self.get(did)
    def add_dataset(self,did,req:DatasetCandidateAddRequest):
        rec=self.get(did); body=req.model_dump(); actor=body.pop("actor_ref"); body["geography"]=_uniq(body["geography"]); body["populations"]=_uniq(body["populations"]); dsid=_id("dataset-",{"source_ref":body["source_ref"],"identifiers":body["identifiers"]})
        item={"dataset_id":dsid,**body,"candidate_only":True,"fitness_certified":False,"human_verified":False,"created_utc":_now()}
        if not any(x["dataset_id"]==dsid for x in rec["dataset_candidates"]): rec["dataset_candidates"].append(item); self._save(rec); self._event(did,"dataset-candidate.added",actor,{"dataset_id":dsid})
        return self.get(did)
    def add_variable(self,did,req:DatasetVariableAddRequest):
        rec=self.get(did); body=req.model_dump(); actor=body.pop("actor_ref"); known={x["dataset_id"] for x in rec["dataset_candidates"]}
        if body["dataset_id"] not in known: raise ValueError("Dataset variable references an unknown dataset_id.")
        vid=_id("var-",{"dataset_id":body["dataset_id"],"name":body["name"],"role":body["role"]}); item={"variable_id":vid,**body,"human_recorded":True,"semantics_certified":False,"created_utc":_now()}
        if not any(x["variable_id"]==vid for x in rec["variables"]): rec["variables"].append(item); self._save(rec); self._event(did,"dataset-variable.added",actor,{"variable_id":vid})
        return self.get(did)
    def assess(self,did,req:DatasetFitnessAssessmentRequest):
        rec=self.get(did); body=req.model_dump(); actor=body.pop("actor_ref"); datasets={x["dataset_id"] for x in rec["dataset_candidates"]}; requirements={x["requirement_id"] for x in rec["data_requirements"]}
        if body["dataset_id"] not in datasets: raise ValueError("Fitness assessment references an unknown dataset_id.")
        body["requirement_ids"]=_uniq(body["requirement_ids"]); missing=[x for x in body["requirement_ids"] if x not in requirements]
        if missing: raise ValueError("Fitness assessment references an unknown requirement_id.")
        aid=_id("fit-",{"dataset_id":body["dataset_id"],"requirement_ids":body["requirement_ids"]}); old=next((x for x in rec["fitness_assessments"] if x["assessment_id"]==aid),None)
        item={"assessment_id":aid,**body,"human_recorded":True,"scientific_validity_certified":False,"updated_utc":_now()}
        if old: old.update(item)
        else: rec["fitness_assessments"].append(item)
        self._save(rec); self._event(did,"dataset-fitness.assessed",actor,{"assessment_id":aid,"decision":body["decision"]}); return self.get(did)
    def set_state(self,did,req:DatasetFitnessStateRequest):
        rec=self.get(did); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(did,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(did)
    def coverage_matrix(self,did):
        rec=self.get(did); vars_by_ds={d["dataset_id"]:{v["name"] for v in rec["variables"] if v["dataset_id"]==d["dataset_id"]} for d in rec["dataset_candidates"]}; rows=[]
        for d in rec["dataset_candidates"]:
            for r in rec["data_requirements"]:
                need=set(r["required_variables"]); have=vars_by_ds[d["dataset_id"]]; rows.append({"dataset_id":d["dataset_id"],"requirement_id":r["requirement_id"],"required_variables":sorted(need),"recorded_variables_present":sorted(need & have),"recorded_variables_missing":sorted(need-have),"structural_coverage_only":True})
        return {"schema":DATASET_DISCOVERY_FITNESS_SCHEMA,"data_fitness_id":did,"rows":rows,"governance":{"coverage_is_metadata_comparison_not_scientific_fitness":True,"missing_metadata_does_not_prove_missing_data":True}}
    def landscape(self,did):
        rec=self.get(did); counts={}
        for x in rec["fitness_assessments"]: counts[x["decision"]]=counts.get(x["decision"],0)+1
        return {"schema":DATASET_DISCOVERY_FITNESS_SCHEMA,"data_fitness_id":did,"datasets":len(rec["dataset_candidates"]),"variables":len(rec["variables"]),"requirements":len(rec["data_requirements"]),"fitness_decisions":counts,"coverage_matrix":self.coverage_matrix(did)["rows"],"governance":{"no_automatic_best_dataset":True,"human_fitness_decision_required":True}}
    def readiness(self,did):
        rec=self.get(did); accepted=[x for x in rec["fitness_assessments"] if x["decision"] in {"fit","fit-with-limitations"}]; blockers=[]
        if not rec["data_requirements"]: blockers.append("no-data-requirements")
        if not rec["dataset_candidates"]: blockers.append("no-dataset-candidates")
        if not accepted: blockers.append("no-human-accepted-fit-assessment")
        if rec["review"]["state"]!="approved": blockers.append("review-not-approved")
        return {"schema":DATASET_DISCOVERY_FITNESS_SCHEMA,"data_fitness_id":did,"ready_for_governed_handoff":not blockers,"blockers":blockers,"accepted_assessment_ids":[x["assessment_id"] for x in accepted],"governance":{"readiness_is_workflow_completeness_not_scientific_validity":True}}
    def computational_planning_handoff(self,did):
        rec=self.get(did); return {"schema":DATASET_DISCOVERY_FITNESS_SCHEMA,"data_fitness_id":did,"write_performed":False,"research_question":rec.get("research_question",""),"accepted_dataset_assessments":[x for x in rec["fitness_assessments"] if x["decision"] in {"fit","fit-with-limitations"}],"datasets":rec["dataset_candidates"],"variables":rec["variables"],"data_requirements":rec["data_requirements"],"target_products":["workspace","research-lab","workbench","catalyst-data"],"governance":{"handoff_is_candidate_payload_not_execution":True,"automatic_ingestion":False}}
    def core_candidate(self,did):
        rec=self.get(did); return {"candidate_id":_id("corecand-",{"data_fitness_id":did,"type":"dataset-discovery-data-fitness"}),"object_type":"dataset-discovery-data-fitness","source_data_fitness_id":did,"payload":{"research_question":rec.get("research_question",""),"gap_novelty_id":rec.get("gap_novelty_id",""),"requirements":rec["data_requirements"],"datasets":rec["dataset_candidates"],"fitness_assessments":rec["fitness_assessments"]},"handoff_status":"human-approved-candidate" if self.readiness(did)["ready_for_governed_handoff"] else "draft-candidate","promotion_performed":False,"governance":{"platform_core_remains_authoritative":True,"candidate_is_not_promoted_object":True}}
    def freeze_snapshot(self,req:DatasetFitnessSnapshotRequest):
        rec=self.get(req.data_fitness_id); payload={"schema":DATASET_DISCOVERY_FITNESS_SNAPSHOT_SCHEMA,"data_fitness_id":req.data_fitness_id,"record":rec,"landscape":self.landscape(req.data_fitness_id),"readiness":self.readiness(req.data_fitness_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_record_not_fitness_certification":True}}
        h=_sha(payload); sid="datafitsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_dataset_fitness_snapshots(snapshot_id,data_fitness_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.data_fitness_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO dataset_fitness_snapshots(snapshot_id,data_fitness_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.data_fitness_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.data_fitness_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid}); return payload

def capabilities():
    return {"schema":DATASET_DISCOVERY_FITNESS_SCHEMA,"release":settings.release_version,"milestone":"10.8","durable":True,"dataset_discovery_is_candidate_generation_not_endorsement":True,"human_fitness_decision_required":True,"fitness_is_question_specific_not_global_quality":True,"license_and_access_require_human_verification":True,"automatic_dataset_suitability":False,"automatic_quality_certification":False,"automatic_variable_semantics_inference":False,"automatic_ingestion":False,"automatic_truth_promotion":False}
_store=None
def get_dataset_discovery_data_fitness_store():
    global _store
    if _store is None: _store=DatasetDiscoveryDataFitnessStore()
    return _store
