from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_question_hypothesis import (
    RESEARCH_QUESTION_HYPOTHESIS_SCHEMA, RESEARCH_QUESTION_HYPOTHESIS_SNAPSHOT_SCHEMA,
    ResearchQuestionPlanCreateRequest, ResearchSubquestionAddRequest, ResearchHypothesisAddRequest,
    ResearchEvidenceRequirementRequest, ResearchQuestionReviewStateRequest, ResearchQuestionSnapshotRequest,
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
def _uniq(values:list[str])->list[str]: return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))
def _slug_id(prefix:str,payload:Any)->str: return prefix+_sha(payload)[:32]

HYPOTHESIS_RELEVANT={"comparative","relational","causal","evaluative","predictive"}
DRIVER_ROLES={"exposure","intervention","predictor"}

class ResearchQuestionHypothesisStore:
    def __init__(self, sqlite_path:Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_question_hypothesis.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres research-question storage requires psycopg.")
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
CREATE TABLE IF NOT EXISTS research_question_plans(plan_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_question_plan_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_question_plan_snapshots(snapshot_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_research_question_plans(plan_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_question_plan_events(event_id BIGSERIAL PRIMARY KEY,plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_research_question_plan_events_plan ON sc_rl_research_question_plan_events(plan_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_question_plan_snapshots(snapshot_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,pid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"plan_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_question_plan_events(plan_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_question_plan_events(plan_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_question_plans(plan_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(plan_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["plan_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO research_question_plans(plan_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["plan_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_research_question_plans WHERE plan_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Research question plan not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM research_question_plans WHERE plan_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Research question plan not found.")
        return json.loads(row["record_json"])

    def _structured_question(self,body:dict[str,Any])->dict[str,Any]:
        variables=body.get("variables") or []
        return {
            "question":body["broad_question"].strip(),"question_type":body.get("question_type","unspecified"),
            "population":body.get("population","").strip(),"context":body.get("context","").strip(),
            "geography":body.get("geography","").strip(),"time_horizon":body.get("time_horizon","").strip(),
            "constructs":_uniq(body.get("constructs") or []),"variables":variables,
        }
    def _candidate_subquestions(self,body:dict[str,Any])->list[dict[str,Any]]:
        q=body["broad_question"].strip(); out=[
            {"question":f"What does the existing evidence base establish about: {q}","purpose":"evidence-landscape","evidence_requirements":["eligible primary and/or high-quality secondary sources"],"core_question_ref":"","origin":"deterministic-scaffold","human_review_status":"unreviewed"},
            {"question":"Under which populations, contexts, geographies, or time horizons could the answer differ?","purpose":"scope-and-boundary-conditions","evidence_requirements":["scope and external-validity evidence"],"core_question_ref":"","origin":"deterministic-scaffold","human_review_status":"unreviewed"},
        ]
        if body.get("variables") or body.get("constructs"):
            out.insert(1,{"question":"How should the key constructs and variables be operationalized and measured?","purpose":"measurement-and-operationalization","evidence_requirements":["measurement definitions and provenance"],"core_question_ref":"","origin":"deterministic-scaffold","human_review_status":"unreviewed"})
        return out
    def _candidate_hypotheses(self,body:dict[str,Any])->list[dict[str,Any]]:
        if body.get("question_type") not in HYPOTHESIS_RELEVANT: return []
        variables=body.get("variables") or []
        driver=next((v for v in variables if v.get("role") in DRIVER_ROLES),None)
        outcome=next((v for v in variables if v.get("role")=="outcome"),None)
        if not driver or not outcome: return []
        d,o=driver["name"],outcome["name"]
        alt={"label":"Candidate alternative hypothesis","statement":f"{d} is associated with a reproducible difference or change in {o} within the defined study scope.","hypothesis_type":"causal" if body.get("question_type")=="causal" else "alternative","expected_direction":"unspecified","rationale":"Deterministic scaffold derived from the supplied variable roles; it is not a scientific conclusion.","falsification_criteria":[f"A pre-specified analysis finds no reproducible relationship or difference between {d} and {o} under the stated design and assumptions."],"core_hypothesis_ref":"","origin":"deterministic-scaffold","human_review_status":"unreviewed"}
        null={"label":"Candidate null hypothesis","statement":f"No reproducible relationship or difference between {d} and {o} is observed within the defined study scope.","hypothesis_type":"null","expected_direction":"no-difference","rationale":"Deterministic companion null hypothesis for review.","falsification_criteria":[f"A pre-specified analysis yields evidence inconsistent with no relationship or difference between {d} and {o}."],"core_hypothesis_ref":"","origin":"deterministic-scaffold","human_review_status":"unreviewed"}
        return [alt,null]
    def create(self,req:ResearchQuestionPlanCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); scaffold=bool(body.pop("scaffold_candidates"))
        body["constructs"]=_uniq(body.get("constructs") or []); body["evidence_requirements"]=_uniq(body.get("evidence_requirements") or []); body["assumptions"]=_uniq(body.get("assumptions") or []); body["falsification_criteria"]=_uniq(body.get("falsification_criteria") or []); body["core_object_refs"]=_uniq(body.get("core_object_refs") or [])
        body["variables"]=[dict(v) for v in body.get("variables") or []]
        body["subquestions"]=[{**dict(x),"origin":"user-supplied","human_review_status":"reviewed"} for x in body.get("subquestions") or []]
        body["hypotheses"]=[{**dict(x),"origin":"user-supplied","human_review_status":"reviewed"} for x in body.get("hypotheses") or []]
        if scaffold:
            if not body["subquestions"]: body["subquestions"]=self._candidate_subquestions(body)
            if not body["hypotheses"]: body["hypotheses"]=self._candidate_hypotheses(body)
            if not body["evidence_requirements"]:
                body["evidence_requirements"]=["source eligibility and provenance criteria","measurement and operationalization support","design-appropriate evidence sufficient to evaluate the research question"]
        for x in body["subquestions"]: x["subquestion_id"]=_slug_id("subq-",{k:v for k,v in x.items() if k!="subquestion_id"})
        for x in body["hypotheses"]: x["hypothesis_id"]=_slug_id("hyp-",{k:v for k,v in x.items() if k!="hypothesis_id"})
        seed={k:v for k,v in body.items() if k not in {"metadata"}}; pid=_slug_id("rqhi-",seed)
        try: return self.get(pid)
        except ValueError: pass
        rec={"schema":RESEARCH_QUESTION_HYPOTHESIS_SCHEMA,"plan_id":pid,**body,"structured_question":self._structured_question(body),"review":{"state":"draft","note":"","actor_ref":"","updated_utc":""},"created_utc":_now(),"updated_utc":_now(),"governance":{"candidate_intelligence_not_scientific_judgment":True,"human_approval_required_for_governed_handoff":True,"platform_core_is_governed_question_hypothesis_authority":True,"automatic_core_write":False,"automatic_hypothesis_acceptance":False,"automatic_causal_inference":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(pid,"plan.created",actor,{"question_type":body.get("question_type"),"scaffold_candidates":scaffold,"subquestion_count":len(rec["subquestions"]),"hypothesis_count":len(rec["hypotheses"])}); return self.get(pid)
    def add_subquestion(self,pid:str,req:ResearchSubquestionAddRequest)->dict[str,Any]:
        rec=self.get(pid); item=req.model_dump(); actor=item.pop("actor_ref"); item.update({"origin":"user-supplied","human_review_status":"reviewed"}); item["subquestion_id"]=_slug_id("subq-",item)
        if not any(x["subquestion_id"]==item["subquestion_id"] for x in rec["subquestions"]): rec["subquestions"].append(item); self._save(rec); self._event(pid,"subquestion.added",actor,{"subquestion_id":item["subquestion_id"]})
        return self.get(pid)
    def add_hypothesis(self,pid:str,req:ResearchHypothesisAddRequest)->dict[str,Any]:
        rec=self.get(pid); item=req.model_dump(); actor=item.pop("actor_ref"); item.update({"origin":"user-supplied","human_review_status":"reviewed"}); item["hypothesis_id"]=_slug_id("hyp-",item)
        if not any(x["hypothesis_id"]==item["hypothesis_id"] for x in rec["hypotheses"]): rec["hypotheses"].append(item); self._save(rec); self._event(pid,"hypothesis.added",actor,{"hypothesis_id":item["hypothesis_id"]})
        return self.get(pid)
    def add_evidence_requirement(self,pid:str,req:ResearchEvidenceRequirementRequest)->dict[str,Any]:
        rec=self.get(pid); value=req.requirement.strip()
        if value not in rec["evidence_requirements"]: rec["evidence_requirements"].append(value); self._save(rec); self._event(pid,"evidence-requirement.added",req.actor_ref,{"requirement":value,"rationale":req.rationale})
        return self.get(pid)
    def set_review_state(self,pid:str,req:ResearchQuestionReviewStateRequest)->dict[str,Any]:
        rec=self.get(pid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"review-state.changed",req.actor_ref,{"state":req.state,"note":req.note}); return self.get(pid)
    def readiness(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); qtype=rec.get("question_type","unspecified"); scope=any(rec.get(k) for k in ["population","context","geography","time_horizon"])
        dimensions={"question_framed":bool(rec.get("broad_question") and rec.get("structured_question")),"scope_defined":scope,"operationalization_started":bool(rec.get("variables") or rec.get("constructs")),"evidence_requirements_defined":bool(rec.get("evidence_requirements")),"hypothesis_strategy_defined":bool(rec.get("hypotheses")) if qtype in HYPOTHESIS_RELEVANT else True,"human_review_approved":rec.get("review",{}).get("state")=="approved"}
        required=["question_framed","scope_defined","operationalization_started","evidence_requirements_defined","hypothesis_strategy_defined"]
        blockers=[k.replace("_","-") for k in required if not dimensions[k]]
        return {"schema":RESEARCH_QUESTION_HYPOTHESIS_SCHEMA,"plan_id":pid,"ready_for_review":not blockers,"ready_for_core_candidate_handoff":not blockers and dimensions["human_review_approved"],"dimensions":dimensions,"blockers":blockers+([] if dimensions["human_review_approved"] else ["human-review-approval"]),"governance":{"readiness_is_structural_not_scientific_validity":True,"human_approval_is_required_for_governed_handoff":True,"no_hypothesis_is_accepted_by_readiness":True}}
    def core_candidates(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); approved=rec.get("review",{}).get("state")=="approved"; candidates=[]
        candidates.append({"candidate_id":_slug_id("corecand-",{"plan_id":pid,"type":"research-question"}),"object_type":"research-question","payload":{"question":rec["broad_question"],"question_type":rec["question_type"],"structured_question":rec["structured_question"],"project_ref":rec["project_ref"]},"source_plan_id":pid})
        for h in rec.get("hypotheses",[]): candidates.append({"candidate_id":_slug_id("corecand-",{"plan_id":pid,"hypothesis_id":h["hypothesis_id"]}),"object_type":"hypothesis","payload":h,"source_plan_id":pid})
        return {"schema":RESEARCH_QUESTION_HYPOTHESIS_SCHEMA,"plan_id":pid,"candidate_count":len(candidates),"candidates":candidates,"handoff_status":"human-approved-candidate-set" if approved else "requires-human-approval","promotion_performed":False,"governance":{"platform_core_remains_authority":True,"automatic_core_write":False,"candidate_generation_is_not_acceptance":True}}
    def freeze_snapshot(self,req:ResearchQuestionSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.plan_id); payload={"schema":RESEARCH_QUESTION_HYPOTHESIS_SNAPSHOT_SCHEMA,"plan_id":req.plan_id,"plan":rec,"readiness":self.readiness(req.plan_id),"core_candidates":self.core_candidates(req.plan_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_planning_record_not_scientific_certification":True}}
        h=_sha(payload); sid="rqh-snap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_question_plan_snapshots(snapshot_id,plan_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.plan_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO research_question_plan_snapshots(snapshot_id,plan_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.plan_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.plan_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":RESEARCH_QUESTION_HYPOTHESIS_SCHEMA,"release":settings.release_version,"milestone":"10.1","durable":True,"deterministic_question_scaffolding":True,"structured_variables_and_constructs":True,"subquestion_registry":True,"candidate_hypothesis_registry":True,"evidence_requirement_registry":True,"falsification_criteria":True,"human_review_state":True,"core_candidate_handoff":True,"platform_core_is_governed_question_hypothesis_authority":True,"automatic_core_write":False,"automatic_hypothesis_acceptance":False,"automatic_causal_inference":False,"automatic_truth_promotion":False,"specialist_method_execution_retained":True}

_store:ResearchQuestionHypothesisStore|None=None
def get_research_question_hypothesis_store()->ResearchQuestionHypothesisStore:
    global _store
    if _store is None: _store=ResearchQuestionHypothesisStore()
    return _store
