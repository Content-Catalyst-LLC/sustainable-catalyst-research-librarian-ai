from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, math, sqlite3, threading, uuid
from pathlib import Path
from statistics import mean
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.rag_evaluation import (
    RAG_EVALUATION_SCHEMA, RAG_EVALUATION_CASE_SCHEMA, RAG_CLAIM_ASSESSMENT_SCHEMA,
    RAG_CITATION_ASSESSMENT_SCHEMA, RAG_EVALUATION_SNAPSHOT_SCHEMA,
    RAGEvaluationCreateRequest, RAGEvaluationCaseRequest, RAGClaimAssessmentRequest,
    RAGCitationAssessmentRequest, RAGEvaluationComparisonRequest, RAGEvaluationSnapshotRequest,
)
from .ai_research_context import get_ai_research_context_store

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

def _retrieval_metrics(expected:list[str], retrieved:list[str], k:int)->dict[str,float|int|None]:
    relevant=set(expected); top=retrieved[:k]
    hits=[1 if x in relevant else 0 for x in top]
    hit_count=sum(hits)
    precision=hit_count/k if k else 0.0
    recall=hit_count/len(relevant) if relevant else None
    rr=None
    for i,x in enumerate(retrieved,1):
        if x in relevant:
            rr=1.0/i; break
    dcg=sum(hit/math.log2(i+2) for i,hit in enumerate(hits))
    ideal_hits=min(len(relevant),k)
    idcg=sum(1.0/math.log2(i+2) for i in range(ideal_hits))
    ndcg=(dcg/idcg) if idcg else None
    return {
        "k":k,"relevant_count":len(relevant),"retrieved_count":len(retrieved),"relevant_retrieved_at_k":hit_count,
        "precision_at_k":precision,"recall_at_k":recall,"reciprocal_rank":rr,"ndcg_at_k":ndcg,
    }

class RAGEvaluationStore:
    def __init__(self, sqlite_path:Path|None=None, context_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"rag_evaluation.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        self.context_store=context_store
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres RAG evaluation storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    def _contexts(self):
        return self.context_store or get_ai_research_context_store()

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
CREATE TABLE IF NOT EXISTS rag_evaluations(evaluation_id TEXT PRIMARY KEY,context_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rag_evaluation_cases(case_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rag_claim_assessments(assessment_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rag_citation_assessments(assessment_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rag_evaluation_snapshots(snapshot_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rag_evaluation_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,evaluation_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluations(evaluation_id TEXT PRIMARY KEY,context_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluation_cases(case_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_rag_claim_assessments(assessment_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_rag_citation_assessments(assessment_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluation_snapshots(snapshot_id TEXT PRIMARY KEY,evaluation_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluation_events(event_id BIGSERIAL PRIMARY KEY,evaluation_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.commit()

    def _event(self,evaluation_id:str,event_type:str,actor_ref:str,payload:dict[str,Any])->None:
        h=_sha({"evaluation_id":evaluation_id,"event_type":event_type,"actor_ref":actor_ref,"payload":payload})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_rag_evaluation_events(evaluation_id,event_type,actor_ref,payload,event_hash) VALUES(%s,%s,%s,%s,%s)",(evaluation_id,event_type,actor_ref,Jsonb(payload),h)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO rag_evaluation_events(evaluation_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(evaluation_id,event_type,actor_ref,_json(payload),h,_now()))

    def create_evaluation(self,req:RAGEvaluationCreateRequest)->dict[str,Any]:
        context=self._contexts().get_context(req.context_id)
        identity={k:v for k,v in req.model_dump().items() if k!="actor_ref"}
        evaluation_id="rageval-"+_sha(identity)[:32]
        rec={"schema":RAG_EVALUATION_SCHEMA,"evaluation_id":evaluation_id,**identity,"context_hash":context["record_hash"],"created_utc":_now(),"governance":{"metrics_are_descriptive":True,"automatic_quality_grade":False,"automatic_model_ranking":False,"automatic_truth_judgment":False,"human_review_required_for_grounding_judgment":True}}
        rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("SELECT record FROM sc_rl_rag_evaluations WHERE evaluation_id=%s",(evaluation_id,)).fetchone()
                if row: rec=dict(row["record"])
                else: c.execute("INSERT INTO sc_rl_rag_evaluations(evaluation_id,context_id,record,record_hash) VALUES(%s,%s,%s,%s)",(evaluation_id,req.context_id,Jsonb(rec),rec["record_hash"])); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                row=c.execute("SELECT record_json FROM rag_evaluations WHERE evaluation_id=?",(evaluation_id,)).fetchone()
                if row: rec=json.loads(row["record_json"])
                else: c.execute("INSERT INTO rag_evaluations(evaluation_id,context_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?)",(evaluation_id,req.context_id,_json(rec),rec["record_hash"],rec["created_utc"]))
        self._event(evaluation_id,"evaluation.created",req.actor_ref,{"record_hash":rec["record_hash"],"context_id":req.context_id})
        return rec

    def get_evaluation(self,evaluation_id:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_rag_evaluations WHERE evaluation_id=%s",(evaluation_id,)).fetchone(); rec=dict(row["record"]) if row else None
        else:
            with self._sqlite() as c: row=c.execute("SELECT record_json FROM rag_evaluations WHERE evaluation_id=?",(evaluation_id,)).fetchone(); rec=json.loads(row["record_json"]) if row else None
        if not rec: raise ValueError(f"Unknown RAG evaluation: {evaluation_id}")
        return rec

    def _records(self,table_pg:str,table_sq:str,evaluation_id:str)->list[dict[str,Any]]:
        self.get_evaluation(evaluation_id)
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute(f"SELECT record FROM {table_pg} WHERE evaluation_id=%s ORDER BY created_utc",(evaluation_id,)).fetchall(); return [dict(x["record"]) for x in rows]
        with self._sqlite() as c: rows=c.execute(f"SELECT record_json FROM {table_sq} WHERE evaluation_id=? ORDER BY created_utc",(evaluation_id,)).fetchall(); return [json.loads(x["record_json"]) for x in rows]

    def _validate_run(self,context_id:str,run_id:str)->None:
        if not run_id: return
        runs=self._contexts().runs(context_id,5000)
        if not any(x.get("run_id")==run_id for x in runs): raise ValueError(f"Retrieval run {run_id} is not registered for context {context_id}.")

    def add_case(self,evaluation_id:str,req:RAGEvaluationCaseRequest)->dict[str,Any]:
        ev=self.get_evaluation(evaluation_id); self._validate_run(ev["context_id"],req.retrieval_run_id)
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}
        metrics=_retrieval_metrics(req.expected_evidence_refs,req.retrieved_evidence_refs,req.k)
        case_id="ragcase-"+_sha({"evaluation_id":evaluation_id,**body})[:32]
        rec={"schema":RAG_EVALUATION_CASE_SCHEMA,"case_id":case_id,"evaluation_id":evaluation_id,**body,"retrieval_metrics":metrics,"created_utc":_now(),"governance":{"relevance_set_is_declared_not_inferred":True,"retrieval_metrics_do_not_imply_answer_validity":True}}
        rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_rag_evaluation_cases(case_id,evaluation_id,record,record_hash) VALUES(%s,%s,%s,%s) ON CONFLICT(case_id) DO NOTHING",(case_id,evaluation_id,Jsonb(rec),rec["record_hash"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO rag_evaluation_cases(case_id,evaluation_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?)",(case_id,evaluation_id,_json(rec),rec["record_hash"],rec["created_utc"]))
        self._event(evaluation_id,"case.registered",req.actor_ref,{"case_id":case_id,"record_hash":rec["record_hash"]})
        return rec

    def add_claim_assessment(self,evaluation_id:str,req:RAGClaimAssessmentRequest)->dict[str,Any]:
        self.get_evaluation(evaluation_id)
        if req.case_id and not any(x["case_id"]==req.case_id for x in self.cases(evaluation_id)): raise ValueError(f"Unknown case for evaluation: {req.case_id}")
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; aid="ragclaim-"+_sha({"evaluation_id":evaluation_id,**body})[:32]
        rec={"schema":RAG_CLAIM_ASSESSMENT_SCHEMA,"assessment_id":aid,"evaluation_id":evaluation_id,**body,"created_utc":_now(),"governance":{"support_status_is_human_or_externally_authored_judgment":True,"not_truth_certification":True}}
        rec["record_hash"]=_sha(rec); self._insert_assessment("sc_rl_rag_claim_assessments","rag_claim_assessments",aid,evaluation_id,rec)
        self._event(evaluation_id,"claim-assessment.registered",req.actor_ref,{"assessment_id":aid,"support_status":req.support_status}); return rec

    def add_citation_assessment(self,evaluation_id:str,req:RAGCitationAssessmentRequest)->dict[str,Any]:
        self.get_evaluation(evaluation_id)
        if req.case_id and not any(x["case_id"]==req.case_id for x in self.cases(evaluation_id)): raise ValueError(f"Unknown case for evaluation: {req.case_id}")
        body={k:v for k,v in req.model_dump().items() if k!="actor_ref"}; aid="ragcite-"+_sha({"evaluation_id":evaluation_id,**body})[:32]
        rec={"schema":RAG_CITATION_ASSESSMENT_SCHEMA,"assessment_id":aid,"evaluation_id":evaluation_id,**body,"created_utc":_now(),"governance":{"citation_status_is_review_record":True,"not_source_quality_score":True}}
        rec["record_hash"]=_sha(rec); self._insert_assessment("sc_rl_rag_citation_assessments","rag_citation_assessments",aid,evaluation_id,rec)
        self._event(evaluation_id,"citation-assessment.registered",req.actor_ref,{"assessment_id":aid,"status":req.status}); return rec

    def _insert_assessment(self,pg:str,sq:str,aid:str,evaluation_id:str,rec:dict[str,Any])->None:
        if self.backend=="postgres":
            with self._postgres() as c: c.execute(f"INSERT INTO {pg}(assessment_id,evaluation_id,record,record_hash) VALUES(%s,%s,%s,%s) ON CONFLICT(assessment_id) DO NOTHING",(aid,evaluation_id,Jsonb(rec),rec["record_hash"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute(f"INSERT OR IGNORE INTO {sq}(assessment_id,evaluation_id,record_json,record_hash,created_utc) VALUES(?,?,?,?,?)",(aid,evaluation_id,_json(rec),rec["record_hash"],rec["created_utc"]))

    def cases(self,evaluation_id:str)->list[dict[str,Any]]: return self._records("sc_rl_rag_evaluation_cases","rag_evaluation_cases",evaluation_id)
    def claim_assessments(self,evaluation_id:str)->list[dict[str,Any]]: return self._records("sc_rl_rag_claim_assessments","rag_claim_assessments",evaluation_id)
    def citation_assessments(self,evaluation_id:str)->list[dict[str,Any]]: return self._records("sc_rl_rag_citation_assessments","rag_citation_assessments",evaluation_id)

    def summary(self,evaluation_id:str)->dict[str,Any]:
        ev=self.get_evaluation(evaluation_id); cases=self.cases(evaluation_id); claims=self.claim_assessments(evaluation_id); cites=self.citation_assessments(evaluation_id)
        def avg(field:str):
            vals=[x["retrieval_metrics"].get(field) for x in cases if x["retrieval_metrics"].get(field) is not None]
            return mean(vals) if vals else None
        reviewed=[x for x in claims if x["support_status"]!="not-assessed"]
        unsupported=sum(x["support_status"]=="unsupported" for x in reviewed); conflicting=sum(x["support_status"]=="conflicting" for x in reviewed)
        cite_reviewed=[x for x in cites if x["status"]!="not-assessed"]
        correct=sum(x["status"]=="correct" for x in cite_reviewed); partial=sum(x["status"]=="partially-correct" for x in cite_reviewed)
        lat=[x["latency_ms"] for x in cases if x.get("latency_ms") is not None]; costs=[x["cost_amount"] for x in cases if x.get("cost_amount") is not None]
        return {"schema":"sc-research-librarian-rag-evaluation-summary/1.0","evaluation_id":evaluation_id,"context_id":ev["context_id"],"counts":{"cases":len(cases),"claim_assessments":len(claims),"citation_assessments":len(cites)},"retrieval":{"mean_precision_at_k":avg("precision_at_k"),"mean_recall_at_k":avg("recall_at_k"),"mean_reciprocal_rank":avg("reciprocal_rank"),"mean_ndcg_at_k":avg("ndcg_at_k")},"grounding":{"reviewed_claims":len(reviewed),"unsupported_claim_rate":unsupported/len(reviewed) if reviewed else None,"conflicting_claim_rate":conflicting/len(reviewed) if reviewed else None},"citations":{"reviewed_citations":len(cite_reviewed),"correct_rate":correct/len(cite_reviewed) if cite_reviewed else None,"correct_or_partial_rate":(correct+partial)/len(cite_reviewed) if cite_reviewed else None},"runtime":{"mean_latency_ms":mean(lat) if lat else None,"total_cost_amount":sum(costs) if costs else None},"governance":{"descriptive_only":True,"no_composite_quality_score":True,"no_automatic_model_ranking":True,"no_truth_judgment":True}}

    def comparison(self,req:RAGEvaluationComparisonRequest)->dict[str,Any]:
        rows=[self.summary(x) for x in req.evaluation_ids]
        return {"schema":"sc-research-librarian-rag-evaluation-comparison/1.0","label":req.label,"evaluations":rows,"governance":{"side_by_side_descriptive_comparison":True,"winner_selected":False,"ranking_generated":False,"human_interpretation_required":True}}

    def freeze_snapshot(self,req:RAGEvaluationSnapshotRequest)->dict[str,Any]:
        payload={"schema":RAG_EVALUATION_SNAPSHOT_SCHEMA,"evaluation":self.get_evaluation(req.evaluation_id),"cases":self.cases(req.evaluation_id),"claim_assessments":self.claim_assessments(req.evaluation_id),"citation_assessments":self.citation_assessments(req.evaluation_id),"summary":self.summary(req.evaluation_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_evaluation_record_not_model_certification":True}}
        h=_sha(payload); sid="ragevalsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_rag_evaluation_snapshots(snapshot_id,evaluation_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.evaluation_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO rag_evaluation_snapshots(snapshot_id,evaluation_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.evaluation_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.evaluation_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":RAG_EVALUATION_SCHEMA,"release":settings.release_version,"durable":True,"evaluation_dimensions":["precision-at-k","recall-at-k","reciprocal-rank","ndcg-at-k","claim-support","citation-correctness","unsupported-claim-rate","conflict-rate","latency","token-usage","cost"],"evaluation_context_is_v960_lineage":True,"human_grounding_review_supported":True,"automatic_truth_judgment":False,"automatic_model_ranking":False,"automatic_quality_grade":False,"automatic_claim_acceptance":False,"metrics_are_evidence_not_verdicts":True}

_store:RAGEvaluationStore|None=None
def get_rag_evaluation_store()->RAGEvaluationStore:
    global _store
    if _store is None: _store=RAGEvaluationStore()
    return _store
