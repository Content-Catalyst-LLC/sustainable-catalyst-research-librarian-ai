from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, re, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.evidence_search_strategy import (
    EVIDENCE_SEARCH_STRATEGY_SCHEMA, EVIDENCE_SEARCH_STRATEGY_SNAPSHOT_SCHEMA,
    EvidenceSearchStrategyCreateRequest, SearchConceptAddRequest, SearchSourceTargetAddRequest,
    SearchQueryAddRequest, SearchEligibilityCriterionRequest, SearchExecutionReceiptRequest,
    EvidenceSearchReviewStateRequest, EvidenceSearchSnapshotRequest,
)
from .research_question_hypothesis import get_research_question_hypothesis_store
from .research_design_methodology import get_research_design_methodology_store

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
def _id(prefix:str,payload:Any)->str: return prefix+_sha(payload)[:32]
def _quote(term:str)->str:
    term=re.sub(r'\s+',' ',str(term).strip())
    return f'"{term}"' if (' ' in term or '-' in term) else term

class EvidenceSearchStrategyStore:
    def __init__(self, sqlite_path:Path|None=None, question_store:Any|None=None, design_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"evidence_search_strategy.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.question_store=question_store; self.design_store=design_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres evidence-search storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _questions(self): return self.question_store or get_research_question_hypothesis_store()
    def _designs(self): return self.design_store or get_research_design_methodology_store()
    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()
    @contextmanager
    def _postgres(self,migration:bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()
    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c: c.executescript("""
CREATE TABLE IF NOT EXISTS evidence_search_strategies(strategy_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence_search_strategy_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,strategy_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence_search_strategy_snapshots(snapshot_id TEXT PRIMARY KEY,strategy_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_evidence_search_strategies(strategy_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_evidence_search_strategy_events(event_id BIGSERIAL PRIMARY KEY,strategy_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_evidence_search_events_strategy ON sc_rl_evidence_search_strategy_events(strategy_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_evidence_search_strategy_snapshots(snapshot_id TEXT PRIMARY KEY,strategy_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,sid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"strategy_id":sid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_evidence_search_strategy_events(strategy_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(sid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO evidence_search_strategy_events(strategy_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(sid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_evidence_search_strategies(strategy_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(strategy_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["strategy_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO evidence_search_strategies(strategy_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["strategy_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,sid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_evidence_search_strategies WHERE strategy_id=%s",(sid,)).fetchone()
            if not row: raise ValueError("Evidence search strategy not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM evidence_search_strategies WHERE strategy_id=?",(sid,)).fetchone()
        if not row: raise ValueError("Evidence search strategy not found.")
        return json.loads(row["record_json"])
    def _question(self,qid:str)->dict[str,Any]:
        if not qid: return {}
        return self._questions().get(qid)
    def _design(self,did:str)->dict[str,Any]:
        if not did: return {}
        return self._designs().get(did)
    def _concept(self,name:str,terms:list[str],description:str="")->dict[str,Any]:
        item={"name":name,"description":description,"terms":_uniq(terms or [name]),"excluded_terms":[]}
        item["concept_id"]=_id("concept-",item); return item
    def _target(self,name:str,family:str,target_ref:str,rationale:str,required:bool=False)->dict[str,Any]:
        item={"name":name,"source_family":family,"target_ref":target_ref,"rationale":rationale,"required":required}
        item["source_target_id"]=_id("source-target-",item); return item
    def _query(self,label:str,text:str,target_refs:list[str],concept_names:list[str],evidence_refs:list[str],filters:dict[str,Any])->dict[str,Any]:
        item={"label":label,"query_text":text,"target_refs":_uniq(target_refs),"concept_names":_uniq(concept_names),"evidence_requirement_refs":_uniq(evidence_refs),"filters":filters}
        item["query_id"]=_id("query-",item); return item
    def _scaffold(self,q:dict[str,Any],d:dict[str,Any],body:dict[str,Any])->tuple[list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]],list[str]]:
        concepts=[]
        for v in q.get("variables",[]) or []:
            name=str(v.get("name") or "").strip()
            if name: concepts.append(self._concept(name,[name],f"Research variable ({v.get('role','unspecified')})."))
        for name,desc in [(q.get("population",""),"Population or unit of analysis."),(q.get("context",""),"Research context or setting.")]:
            if str(name).strip(): concepts.append(self._concept(str(name),[str(name)],desc))
        if not concepts and body.get("research_question"):
            concepts.append(self._concept("research question",[body["research_question"]],"Fallback whole-question concept; refine before execution."))
        dedup={x["concept_id"]:x for x in concepts}; concepts=list(dedup.values())
        targets=[
            self._target("Sustainable Catalyst Knowledge Library","knowledge-library","knowledge-library","Search the governed local publication/source corpus first.",True),
            self._target("Research Librarian Federated Discovery","federated-discovery","federated-discovery","Prepare discovery across configured external providers without importing sources automatically.",False),
        ]
        evidence=_uniq((body.get("evidence_requirements") or [])+(q.get("evidence_requirements") or []))
        preferred=d.get("preferred_candidate_id","")
        selected=next((x for x in d.get("candidate_designs",[]) if x.get("candidate_id")==preferred),None)
        if selected:
            evidence=_uniq(evidence+(selected.get("data_requirements") or []))
        clauses=[]
        for c in concepts[:8]:
            terms=_uniq(c.get("terms",[]))
            if terms: clauses.append("("+" OR ".join(_quote(t) for t in terms[:12])+")")
        base=" AND ".join(clauses) if clauses else _quote(body.get("research_question") or "research evidence")
        filters={"languages":body.get("languages") or ["English"],"date_start":body.get("date_start","") ,"date_end":body.get("date_end","") ,"source_types":body.get("source_types") or []}
        refs=[x["target_ref"] for x in targets]
        queries=[self._query("Primary concept search",base,refs,[x["name"] for x in concepts],evidence,filters)]
        if q.get("hypotheses"):
            for i,h in enumerate(q.get("hypotheses",[])[:20],1):
                statement=str(h.get("statement") or "").strip()
                if statement: queries.append(self._query(f"Hypothesis search {i}",_quote(statement),refs,[],[str(h.get("hypothesis_id") or "")],filters))
        return concepts,targets,queries,evidence
    def create(self,req:EvidenceSearchStrategyCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); scaffold=body.pop("scaffold_strategy")
        q=self._question(body.get("question_plan_id","")); d=self._design(body.get("research_design_plan_id",""))
        if q and not body.get("research_question"): body["research_question"]=q.get("broad_question","")
        sc_concepts,sc_targets,sc_queries,sc_evidence=self._scaffold(q,d,body) if scaffold else ([],[],[],[])
        concepts=[]
        for x in body.get("concepts",[]):
            item=dict(x); item["terms"]=_uniq(item.get("terms") or [item.get("name","")]); item["excluded_terms"]=_uniq(item.get("excluded_terms") or []); item["concept_id"]=_id("concept-",item); concepts.append(item)
        targets=[]
        for x in body.get("source_targets",[]):
            item=dict(x); item["source_target_id"]=_id("source-target-",item); targets.append(item)
        queries=[]
        for x in body.get("queries",[]):
            item=dict(x); item["target_refs"]=_uniq(item.get("target_refs") or []); item["concept_names"]=_uniq(item.get("concept_names") or []); item["evidence_requirement_refs"]=_uniq(item.get("evidence_requirement_refs") or []); item["query_id"]=_id("query-",item); queries.append(item)
        body["concepts"]=concepts or sc_concepts; body["source_targets"]=targets or sc_targets; body["queries"]=queries or sc_queries
        body["evidence_requirements"]=_uniq((body.get("evidence_requirements") or [])+sc_evidence)
        body["inclusion_criteria"]=_uniq(body.get("inclusion_criteria") or ["Source materially addresses the research question, a registered evidence requirement, or a defined research-design data requirement.","Source identity and provenance are sufficient to cite or trace."])
        body["exclusion_criteria"]=_uniq(body.get("exclusion_criteria") or ["Duplicate source instance without additional evidentiary value.","Source cannot be traced sufficiently for reproducible review."])
        body["languages"]=_uniq(body.get("languages") or ["English"]); body["source_types"]=_uniq(body.get("source_types") or [])
        seed={k:v for k,v in body.items() if k!="metadata"}; sid=_id("essp-",seed)
        try: return self.get(sid)
        except ValueError: pass
        rec={"schema":EVIDENCE_SEARCH_STRATEGY_SCHEMA,"strategy_id":sid,**body,"execution_receipts":[],"review":{"state":"draft","note":"","actor_ref":"","updated_utc":""},"created_utc":_now(),"updated_utc":_now(),"governance":{"strategy_is_reproducible_search_plan_not_source_acceptance":True,"human_search_protocol_approval_required":True,"source_screening_and_evidence_acceptance_remain_separate":True,"knowledge_library_owns_source_ingestion_and_retrieval":True,"platform_core_remains_governed_evidence_object_authority":True,"automatic_external_search_execution":False,"automatic_source_acceptance":False,"automatic_quality_judgment":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(sid,"search-strategy.created",actor,{"question_plan_id":rec.get("question_plan_id"),"research_design_plan_id":rec.get("research_design_plan_id"),"query_count":len(rec["queries"])}); return self.get(sid)
    def add_concept(self,sid:str,req:SearchConceptAddRequest)->dict[str,Any]:
        rec=self.get(sid); item=req.model_dump(); actor=item.pop("actor_ref"); item["terms"]=_uniq(item.get("terms") or [item.get("name","")]); item["excluded_terms"]=_uniq(item.get("excluded_terms") or []); item["concept_id"]=_id("concept-",item)
        if not any(x["concept_id"]==item["concept_id"] for x in rec["concepts"]): rec["concepts"].append(item); self._save(rec); self._event(sid,"concept.added",actor,{"concept_id":item["concept_id"]})
        return self.get(sid)
    def add_source_target(self,sid:str,req:SearchSourceTargetAddRequest)->dict[str,Any]:
        rec=self.get(sid); item=req.model_dump(); actor=item.pop("actor_ref"); item["source_target_id"]=_id("source-target-",item)
        if not any(x["source_target_id"]==item["source_target_id"] for x in rec["source_targets"]): rec["source_targets"].append(item); self._save(rec); self._event(sid,"source-target.added",actor,{"source_target_id":item["source_target_id"]})
        return self.get(sid)
    def add_query(self,sid:str,req:SearchQueryAddRequest)->dict[str,Any]:
        rec=self.get(sid); item=req.model_dump(); actor=item.pop("actor_ref"); item["target_refs"]=_uniq(item.get("target_refs") or []); item["concept_names"]=_uniq(item.get("concept_names") or []); item["evidence_requirement_refs"]=_uniq(item.get("evidence_requirement_refs") or []); item["query_id"]=_id("query-",item)
        if not any(x["query_id"]==item["query_id"] for x in rec["queries"]): rec["queries"].append(item); self._save(rec); self._event(sid,"query.added",actor,{"query_id":item["query_id"]})
        return self.get(sid)
    def add_criterion(self,sid:str,req:SearchEligibilityCriterionRequest)->dict[str,Any]:
        rec=self.get(sid); key="inclusion_criteria" if req.mode=="include" else "exclusion_criteria"; value=req.criterion.strip()
        if value not in rec[key]: rec[key].append(value); self._save(rec); self._event(sid,"criterion.added",req.actor_ref,{"mode":req.mode,"criterion":value,"rationale":req.rationale})
        return self.get(sid)
    def add_execution_receipt(self,sid:str,req:SearchExecutionReceiptRequest)->dict[str,Any]:
        rec=self.get(sid)
        if not any(x.get("query_id")==req.query_id for x in rec.get("queries",[])): raise ValueError("Search query not found.")
        item=req.model_dump(); actor=item.pop("actor_ref"); identity={k:v for k,v in item.items() if k!="executed_utc"}; item["receipt_id"]=_id("search-receipt-",identity); item["executed_utc"]=item.get("executed_utc") or _now()
        if not any(x["receipt_id"]==item["receipt_id"] for x in rec["execution_receipts"]): rec["execution_receipts"].append(item); self._save(rec); self._event(sid,"execution-receipt.recorded",actor,{"receipt_id":item["receipt_id"],"query_id":item["query_id"]})
        return self.get(sid)
    def set_review_state(self,sid:str,req:EvidenceSearchReviewStateRequest)->dict[str,Any]:
        rec=self.get(sid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(sid,"review-state.changed",req.actor_ref,{"state":req.state,"note":req.note}); return self.get(sid)
    def coverage(self,sid:str)->dict[str,Any]:
        rec=self.get(sid); rows=[]
        for requirement in rec.get("evidence_requirements",[]):
            qids=[q["query_id"] for q in rec.get("queries",[]) if requirement in (q.get("evidence_requirement_refs") or [])]
            rows.append({"evidence_requirement":requirement,"query_ids":qids,"covered":bool(qids)})
        return {"schema":EVIDENCE_SEARCH_STRATEGY_SCHEMA,"strategy_id":sid,"evidence_requirement_coverage":rows,"covered":sum(1 for x in rows if x["covered"]),"total":len(rows),"governance":{"coverage_is_protocol_mapping_not_evidence_sufficiency":True}}
    def readiness(self,sid:str)->dict[str,Any]:
        rec=self.get(sid); cov=self.coverage(sid); req_total=cov["total"]
        dimensions={"research_question_bound":bool(rec.get("question_plan_id") or rec.get("research_question")),"concepts_defined":bool(rec.get("concepts")),"source_targets_defined":bool(rec.get("source_targets")),"queries_defined":bool(rec.get("queries")),"inclusion_criteria_defined":bool(rec.get("inclusion_criteria")),"exclusion_criteria_defined":bool(rec.get("exclusion_criteria")),"evidence_requirements_mapped":True if req_total==0 else cov["covered"]==req_total,"human_review_approved":rec.get("review",{}).get("state")=="approved"}
        required=["research_question_bound","concepts_defined","source_targets_defined","queries_defined","inclusion_criteria_defined","exclusion_criteria_defined","evidence_requirements_mapped"]
        blockers=[x.replace("_","-") for x in required if not dimensions[x]]
        return {"schema":EVIDENCE_SEARCH_STRATEGY_SCHEMA,"strategy_id":sid,"ready_for_protocol_review":not blockers,"ready_for_search_handoff":not blockers and dimensions["human_review_approved"],"dimensions":dimensions,"blockers":blockers+([] if dimensions["human_review_approved"] else ["human-review-approval"]),"governance":{"readiness_is_structural_not_search_completeness_or_evidence_quality":True,"human_approval_required_before_search_handoff":True}}
    def execution_handoffs(self,sid:str)->dict[str,Any]:
        rec=self.get(sid); approved=rec.get("review",{}).get("state")=="approved"; packets=[]
        for q in rec.get("queries",[]):
            targets=q.get("target_refs") or [x.get("target_ref") for x in rec.get("source_targets",[]) if x.get("target_ref")]
            for target in _uniq(targets):
                packets.append({"handoff_id":_id("search-handoff-",{"strategy_id":sid,"query_id":q["query_id"],"target":target}),"target":target,"strategy_id":sid,"query":q,"eligibility":{"include":rec.get("inclusion_criteria",[]),"exclude":rec.get("exclusion_criteria",[])},"status":"human-approved-protocol" if approved else "requires-human-approval"})
        return {"schema":EVIDENCE_SEARCH_STRATEGY_SCHEMA,"strategy_id":sid,"handoffs":packets,"delivery_performed":False,"search_executed":False,"sources_imported":False,"governance":{"knowledge_library_or_connector_runtime_executes_search":True,"automatic_external_search_execution":False,"automatic_source_import":False,"automatic_source_acceptance":False}}
    def core_candidate(self,sid:str)->dict[str,Any]:
        rec=self.get(sid); approved=rec.get("review",{}).get("state")=="approved"
        candidate={"candidate_id":_id("corecand-",{"strategy_id":sid,"type":"evidence-search-protocol"}),"object_type":"evidence-search-protocol","payload":{"question_plan_id":rec.get("question_plan_id",""),"research_design_plan_id":rec.get("research_design_plan_id",""),"research_question":rec.get("research_question",""),"queries":rec.get("queries",[]),"source_targets":rec.get("source_targets",[]),"eligibility":{"include":rec.get("inclusion_criteria",[]),"exclude":rec.get("exclusion_criteria",[])},"coverage":self.coverage(sid)},"source_strategy_id":sid}
        return {"schema":EVIDENCE_SEARCH_STRATEGY_SCHEMA,"strategy_id":sid,"candidate":candidate,"handoff_status":"human-approved-candidate" if approved else "requires-human-approval","promotion_performed":False,"governance":{"platform_core_remains_authority":True,"automatic_core_write":False,"search_protocol_is_not_evidence_acceptance":True}}
    def freeze_snapshot(self,req:EvidenceSearchSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.strategy_id); payload={"schema":EVIDENCE_SEARCH_STRATEGY_SNAPSHOT_SCHEMA,"strategy_id":req.strategy_id,"strategy":rec,"coverage":self.coverage(req.strategy_id),"readiness":self.readiness(req.strategy_id),"execution_handoffs":self.execution_handoffs(req.strategy_id),"core_candidate":self.core_candidate(req.strategy_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_search_protocol_record_not_evidence_quality_certification":True}}
        h=_sha(payload); snap="ess-snap-"+h[:32]; payload.update({"snapshot_id":snap,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_evidence_search_strategy_snapshots(snapshot_id,strategy_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(snap,req.strategy_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO evidence_search_strategy_snapshots(snapshot_id,strategy_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(snap,req.strategy_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.strategy_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":snap,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":EVIDENCE_SEARCH_STRATEGY_SCHEMA,"release":settings.release_version,"milestone":"10.3","durable":True,"question_plan_integration":True,"research_design_plan_integration":True,"concept_and_synonym_registry":True,"source_target_registry":True,"reproducible_boolean_query_planning":True,"inclusion_exclusion_protocol":True,"evidence_requirement_coverage_mapping":True,"search_execution_receipts":True,"knowledge_library_search_handoffs":True,"federated_discovery_handoffs":True,"platform_core_protocol_candidate":True,"human_search_protocol_approval_required":True,"automatic_external_search_execution":False,"automatic_source_import":False,"automatic_source_acceptance":False,"automatic_quality_judgment":False,"automatic_truth_promotion":False,"knowledge_library_owns_source_ingestion_and_retrieval":True}

_store:EvidenceSearchStrategyStore|None=None
def get_evidence_search_strategy_store()->EvidenceSearchStrategyStore:
    global _store
    if _store is None: _store=EvidenceSearchStrategyStore()
    return _store
