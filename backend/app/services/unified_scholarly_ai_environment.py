from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.unified_scholarly_ai_environment import (
    UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA, UNIFIED_SCHOLARLY_AI_DOSSIER_SCHEMA,
    UNIFIED_SCHOLARLY_AI_SNAPSHOT_SCHEMA, UnifiedResearchEnvironmentCreateRequest,
    UnifiedResearchEnvironmentBindingRequest, UnifiedResearchEnvironmentSnapshotRequest,
)
from .research_workflow import get_research_workflow_store
from .scholarly_research import get_scholarly_research_store
from .peer_review import get_peer_review_store
from .scholarly_publication import get_scholarly_publication_store
from .research_knowledge_graph import get_research_knowledge_graph_store
from .ai_research_context import get_ai_research_context_store
from .rag_evaluation import get_rag_evaluation_store
from .ai_research_experiment import get_ai_research_experiment_store
from .model_aware_exchange import get_model_aware_research_store
from .research_question_hypothesis import get_research_question_hypothesis_store
from .research_design_methodology import get_research_design_methodology_store
from .evidence_search_strategy import get_evidence_search_strategy_store

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

class UnifiedScholarlyAIEnvironmentStore:
    def __init__(self, sqlite_path:Path|None=None, **stores:Any)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"unified_scholarly_ai_environment.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock(); self.stores=stores
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres unified research environment storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    def _store(self,key:str,default): return self.stores.get(key) or default()
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
CREATE TABLE IF NOT EXISTS unified_research_environments(environment_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS unified_research_environment_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,environment_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS unified_research_environment_snapshots(snapshot_id TEXT PRIMARY KEY,environment_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_unified_research_environments(environment_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_unified_research_environment_events(event_id BIGSERIAL PRIMARY KEY,environment_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_unified_environment_events_env ON sc_rl_unified_research_environment_events(environment_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_unified_research_environment_snapshots(snapshot_id TEXT PRIMARY KEY,environment_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,eid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"environment_id":eid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_unified_research_environment_events(environment_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(eid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO unified_research_environment_events(environment_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(eid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_unified_research_environments(environment_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(environment_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["environment_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO unified_research_environments(environment_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["environment_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,eid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_unified_research_environments WHERE environment_id=%s",(eid,)).fetchone();
            if not row: raise ValueError("Unified research environment not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM unified_research_environments WHERE environment_id=?",(eid,)).fetchone()
        if not row: raise ValueError("Unified research environment not found.")
        return json.loads(row["record_json"])
    def create(self,req:UnifiedResearchEnvironmentCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref")
        initial=[]
        singles=[("research-workflow",body.pop("workflow_id")),("scholarly-study",body.pop("study_id")),("scholarly-publication",body.pop("publication_id"))]
        multiples=[("ai-research-context",body.pop("context_ids")),("rag-evaluation",body.pop("evaluation_ids")),("ai-research-experiment",body.pop("experiment_ids")),("model-aware-research",body.pop("model_aware_record_ids")),("cross-product-exchange",body.pop("exchange_ids")),("research-question-plan",body.pop("question_plan_ids")),("research-design-plan",body.pop("research_design_plan_ids")),("evidence-search-strategy-plan",body.pop("evidence_search_strategy_ids")),("knowledge-graph-node",body.pop("knowledge_graph_node_refs")),("core-object",body.pop("core_object_refs"))]
        for typ,ref in singles:
            if ref: initial.append({"component_type":typ,"ref":ref,"role":"primary","note":""})
        for typ,refs in multiples:
            for ref in _uniq(refs): initial.append({"component_type":typ,"ref":ref,"role":"","note":""})
        seed={**body,"bindings":initial}; eid="urai-"+_sha(seed)[:32]
        try: return self.get(eid)
        except ValueError: pass
        rec={"schema":UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA,"environment_id":eid,**body,"bindings":initial,"created_utc":_now(),"updated_utc":_now(),"governance":{"environment_is_orchestration_and_lineage_not_new_authority":True,"component_authority_remains_with_source_system":True,"platform_core_governance_remains_external":True,"automatic_truth_promotion":False,"automatic_scholarly_judgment":False,"automatic_model_selection":False,"automatic_execution":False}}
        self._save(rec); self._event(eid,"environment.created",actor,{"binding_count":len(initial)}); return self.get(eid)
    def bind(self,eid:str,req:UnifiedResearchEnvironmentBindingRequest)->dict[str,Any]:
        rec=self.get(eid); item={"component_type":req.component_type,"ref":req.ref.strip(),"role":req.role,"note":req.note}
        if not any(x["component_type"]==item["component_type"] and x["ref"]==item["ref"] for x in rec["bindings"]):
            rec["bindings"].append(item); self._save(rec); self._event(eid,"binding.added",req.actor_ref,item)
        return self.get(eid)
    def _refs(self,rec:dict[str,Any],typ:str)->list[str]: return [x["ref"] for x in rec.get("bindings",[]) if x.get("component_type")==typ]
    def lineage(self,eid:str)->dict[str,Any]:
        rec=self.get(eid); out={"schema":UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA,"environment_id":eid,"project_ref":rec["project_ref"],"research_design":{},"scholarly":{},"ai":{},"knowledge":{},"exchange":{},"unresolved":[]}
        def one(typ,key,fn):
            refs=self._refs(rec,typ)
            if refs:
                try: out[key]=fn(refs[0])
                except Exception as exc: out["unresolved"].append({"component_type":typ,"ref":refs[0],"error":str(exc)})
        out["research_design"]["question_plans"]=[]
        for ref in self._refs(rec,"research-question-plan"):
            try:
                qs=self._store("question_store",get_research_question_hypothesis_store)
                out["research_design"]["question_plans"].append({"plan":qs.get(ref),"readiness":qs.readiness(ref)})
            except Exception as exc: out["unresolved"].append({"component_type":"research-question-plan","ref":ref,"error":str(exc)})
        out["research_design"]["methodology_plans"]=[]
        for ref in self._refs(rec,"research-design-plan"):
            try:
                ds=self._store("design_store",get_research_design_methodology_store)
                out["research_design"]["methodology_plans"].append({"plan":ds.get(ref),"readiness":ds.readiness(ref),"comparison":ds.comparison(ref)})
            except Exception as exc: out["unresolved"].append({"component_type":"research-design-plan","ref":ref,"error":str(exc)})
        out["research_design"]["search_strategies"]=[]
        for ref in self._refs(rec,"evidence-search-strategy-plan"):
            try:
                es=self._store("search_store",get_evidence_search_strategy_store)
                out["research_design"]["search_strategies"].append({"strategy":es.get(ref),"readiness":es.readiness(ref),"coverage":es.coverage(ref)})
            except Exception as exc: out["unresolved"].append({"component_type":"evidence-search-strategy-plan","ref":ref,"error":str(exc)})
        one("research-workflow","workflow",lambda x:self._store("workflow_store",get_research_workflow_store).get(x))
        srefs=self._refs(rec,"scholarly-study")
        if srefs:
            sid=srefs[0]
            try:
                st=self._store("scholarly_store",get_scholarly_research_store); out["scholarly"]["study"]=st.get(sid); out["scholarly"]["study_readiness"]=st.readiness(sid)
            except Exception as exc: out["unresolved"].append({"component_type":"scholarly-study","ref":sid,"error":str(exc)})
            try:
                pr=self._store("peer_store",get_peer_review_store); out["scholarly"]["peer_review"]=pr.get(sid,create_if_missing=False); out["scholarly"]["peer_review_readiness"]=pr.readiness(sid)
            except Exception: pass
        one("scholarly-publication","publication",lambda x:self._store("publication_store",get_scholarly_publication_store).get(x))
        ctx=self._refs(rec,"ai-research-context"); evs=self._refs(rec,"rag-evaluation"); exps=self._refs(rec,"ai-research-experiment"); mars=self._refs(rec,"model-aware-research")
        out["ai"]["contexts"]=[]; out["ai"]["evaluations"]=[]; out["ai"]["experiments"]=[]; out["ai"]["model_aware_records"]=[]
        for ref in ctx:
            try: out["ai"]["contexts"].append(self._store("context_store",get_ai_research_context_store).lineage(ref))
            except Exception as exc: out["unresolved"].append({"component_type":"ai-research-context","ref":ref,"error":str(exc)})
        for ref in evs:
            try: out["ai"]["evaluations"].append(self._store("evaluation_store",get_rag_evaluation_store).summary(ref))
            except Exception as exc: out["unresolved"].append({"component_type":"rag-evaluation","ref":ref,"error":str(exc)})
        for ref in exps:
            try: out["ai"]["experiments"].append(self._store("experiment_store",get_ai_research_experiment_store).summary(ref))
            except Exception as exc: out["unresolved"].append({"component_type":"ai-research-experiment","ref":ref,"error":str(exc)})
        for ref in mars:
            try: out["ai"]["model_aware_records"].append(self._store("model_aware_store",get_model_aware_research_store).lineage(ref))
            except Exception as exc: out["unresolved"].append({"component_type":"model-aware-research","ref":ref,"error":str(exc)})
        out["knowledge"]["graph_nodes"]=[]
        for ref in self._refs(rec,"knowledge-graph-node"):
            try: out["knowledge"]["graph_nodes"].append(self._store("graph_store",get_research_knowledge_graph_store).neighborhood(ref,limit=100))
            except Exception as exc: out["unresolved"].append({"component_type":"knowledge-graph-node","ref":ref,"error":str(exc)})
        out["exchange"]["packets"]=[]
        for ref in self._refs(rec,"cross-product-exchange"):
            try: out["exchange"]["packets"].append(self._store("model_aware_store",get_model_aware_research_store).get_exchange(ref))
            except Exception as exc: out["unresolved"].append({"component_type":"cross-product-exchange","ref":ref,"error":str(exc)})
        out["core_object_refs"]=_uniq(self._refs(rec,"core-object")); out["governance"]={"lineage_is_assembled_not_promoted":True,"missing_components_are_reported_not_inferred":True,"quality_or_truth_not_inferred":True}
        return out
    def readiness(self,eid:str)->dict[str,Any]:
        rec=self.get(eid); line=self.lineage(eid)
        dimensions={
            "project_bound":bool(rec.get("project_ref")),
            "question_plan_bound":bool(self._refs(rec,"research-question-plan")),
            "research_design_plan_bound":bool(self._refs(rec,"research-design-plan")),
            "evidence_search_strategy_bound":bool(self._refs(rec,"evidence-search-strategy-plan")),
            "scholarly_lineage_bound":bool(self._refs(rec,"scholarly-study") or self._refs(rec,"scholarly-publication")),
            "ai_lineage_bound":bool(self._refs(rec,"ai-research-context") or self._refs(rec,"ai-research-experiment") or self._refs(rec,"model-aware-research")),
            "all_bound_components_resolved":not line["unresolved"],
            "publication_bound":bool(self._refs(rec,"scholarly-publication")),
            "cross_product_exchange_bound":bool(self._refs(rec,"cross-product-exchange")),
        }
        required=["project_bound","scholarly_lineage_bound","ai_lineage_bound","all_bound_components_resolved"]
        blockers=[k.replace("_","-") for k in required if not dimensions[k]]
        return {"schema":UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA,"environment_id":eid,"ready":not blockers,"dimensions":dimensions,"blockers":blockers,"unresolved":line["unresolved"],"governance":{"readiness_is_structural_completeness_not_scientific_validity":True,"publication_and_exchange_are_optional_maturity_dimensions":True,"automatic_truth_promotion":False}}
    def dossier(self,eid:str)->dict[str,Any]:
        rec=self.get(eid); line=self.lineage(eid); ready=self.readiness(eid)
        return {"schema":UNIFIED_SCHOLARLY_AI_DOSSIER_SCHEMA,"environment":{"environment_id":eid,"title":rec["title"],"research_question":rec.get("research_question","") ,"project_ref":rec["project_ref"],"record_hash":rec["record_hash"]},"bindings":rec["bindings"],"lineage":line,"readiness":ready,"lifecycle":["research-question-and-hypothesis-intelligence","research-design-and-methodology-planning","evidence-search-strategy","workflow","scholarly-study","evidence-and-analysis","ai-context","rag-evaluation","ai-experiment","model-aware-lineage","peer-review-and-replication","publication","knowledge-graph","cross-product-exchange"],"governance":{"dossier_is_assembled_view_not_new_source_of_truth":True,"human_scholarly_judgment_preserved":True,"specialist_runtime_execution_preserved":True,"platform_core_governance_preserved":True}}
    def freeze_snapshot(self,req:UnifiedResearchEnvironmentSnapshotRequest)->dict[str,Any]:
        dossier=self.dossier(req.environment_id); payload={"schema":UNIFIED_SCHOLARLY_AI_SNAPSHOT_SCHEMA,"environment_id":req.environment_id,"dossier":dossier,"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_environment_record_not_truth_certification":True}}
        h=_sha(payload); sid="uraisnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_unified_research_environment_snapshots(snapshot_id,environment_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.environment_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO unified_research_environment_snapshots(snapshot_id,environment_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.environment_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.environment_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":UNIFIED_SCHOLARLY_AI_ENVIRONMENT_SCHEMA,"release":settings.release_version,"milestone":"10.0","durable":True,"component_types":["research-question-plan","research-design-plan","evidence-search-strategy-plan","research-workflow","scholarly-study","scholarly-publication","knowledge-graph-node","ai-research-context","rag-evaluation","ai-research-experiment","model-aware-research","cross-product-exchange","core-object"],"unifies":["research-question-and-hypothesis-intelligence","research-design-and-methodology-planning","evidence-search-strategy","scholarly-research","peer-review-and-replication","publication","knowledge-graph","ai-context","rag-evaluation","ai-experiments","model-aware-lineage","cross-product-exchange"],"component_authority_remains_with_source_system":True,"platform_core_governance_remains_external":True,"automatic_execution":False,"automatic_model_selection":False,"automatic_scholarly_judgment":False,"automatic_truth_promotion":False}

_store:UnifiedScholarlyAIEnvironmentStore|None=None
def get_unified_scholarly_ai_environment_store()->UnifiedScholarlyAIEnvironmentStore:
    global _store
    if _store is None: _store=UnifiedScholarlyAIEnvironmentStore()
    return _store
