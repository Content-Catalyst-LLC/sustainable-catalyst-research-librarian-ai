from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_program_intelligence import *
from .computational_research_planning import get_computational_research_planning_store
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

class ResearchProgramIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None,computational_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_program_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.computational_store=computational_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres research program intelligence storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _computational(self): return self.computational_store or get_computational_research_planning_store()
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
CREATE TABLE IF NOT EXISTS research_programs(research_program_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_program_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,research_program_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_program_snapshots(snapshot_id TEXT PRIMARY KEY,research_program_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_research_programs(research_program_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_program_events(event_id BIGSERIAL PRIMARY KEY,research_program_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_research_program_events_program ON sc_rl_research_program_events(research_program_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_program_snapshots(snapshot_id TEXT PRIMARY KEY,research_program_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,pid,typ,actor,payload):
        created=_now(); h=_sha({"research_program_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_program_events(research_program_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_program_events(research_program_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_programs(research_program_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(research_program_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["research_program_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO research_programs(research_program_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["research_program_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_research_programs WHERE research_program_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Research program not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM research_programs WHERE research_program_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Research program not found.")
        return json.loads(row["record_json"])
    def create(self,req:ResearchProgramCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref"); body["research_objectives"]=_uniq(body["research_objectives"]); body["computational_plan_ids"]=_uniq(body["computational_plan_ids"])
        upstream=[]
        for cid in body["computational_plan_ids"]:
            try: upstream.append(self._computational().get(cid))
            except Exception as exc: raise ValueError("One or more computational_plan_ids are not available in Computational Research Planning.") from exc
        if not body.get("core_project_id"):
            cores=_uniq([x.get("core_project_id","") for x in upstream]); body["core_project_id"]=cores[0] if len(cores)==1 else ""
        pid=_id("rprog-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(pid)
        except ValueError: pass
        bindings=[]
        for plan in upstream:
            bid=_id("pbind-",{"component_type":"computational-research-plan","component_ref":plan["computational_plan_id"],"workstream_id":"","role":"planned-computation"})
            bindings.append({"binding_id":bid,"component_type":"computational-research-plan","component_ref":plan["computational_plan_id"],"workstream_id":"","role":"planned-computation","source_authority":"research-librarian-computational-research-planning","note":"","resolution_status":"resolved","source_fingerprint":plan.get("record_hash",""),"human_recorded":True,"created_utc":_now()})
        rec={"schema":RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA,"research_program_id":pid,**body,"computational_plan_fingerprints":{x["computational_plan_id"]:x.get("record_hash","") for x in upstream},"workstreams":[],"component_bindings":bindings,"milestones":[],"milestone_decisions":[],"deliverables":[],"constraints":[],"review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),"governance":{"program_is_coordination_and_lineage_not_scientific_authority":True,"human_program_approval_required":True,"component_authority_remains_with_source_system":True,"platform_core_remains_research_object_authority":True,"specialist_runtimes_own_execution":True,"automatic_research_prioritization":False,"automatic_resource_allocation":False,"automatic_milestone_completion":False,"automatic_scientific_judgment":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(pid,"research-program.created",actor,{"computational_plan_count":len(upstream)}); return self.get(pid)
    def add_workstream(self,pid,req:ResearchProgramWorkstreamAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["computational_plan_ids"]=_uniq(body["computational_plan_ids"]); body["dependencies"]=_uniq(body["dependencies"]); body["expected_outputs"]=_uniq(body["expected_outputs"])
        known_plans=set(rec.get("computational_plan_ids",[])); missing=[x for x in body["computational_plan_ids"] if x not in known_plans]
        if missing: raise ValueError("Workstream references an unknown computational_plan_id.")
        known_ws={x["workstream_id"] for x in rec["workstreams"]}; baddeps=[x for x in body["dependencies"] if x not in known_ws]
        if baddeps: raise ValueError("Workstream references an unknown dependency workstream_id.")
        wid=_id("workstream-",{"label":body["label"],"objective":body["objective"],"computational_plan_ids":body["computational_plan_ids"],"dependencies":body["dependencies"]})
        item={"workstream_id":wid,**body,"human_recorded":True,"scientific_validity_certified":False,"created_utc":_now()}
        if not any(x["workstream_id"]==wid for x in rec["workstreams"]): rec["workstreams"].append(item); self._save(rec); self._event(pid,"workstream.added",actor,{"workstream_id":wid})
        return self.get(pid)
    def bind_component(self,pid,req:ResearchProgramComponentBindingRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref")
        if body["workstream_id"] and body["workstream_id"] not in {x["workstream_id"] for x in rec["workstreams"]}: raise ValueError("Component binding references an unknown workstream_id.")
        resolved=False; fingerprint=""
        if body["component_type"]=="computational-research-plan":
            try: plan=self._computational().get(body["component_ref"]); resolved=True; fingerprint=plan.get("record_hash","")
            except Exception as exc: raise ValueError("Computational component binding references an unknown computational plan.") from exc
            if body["component_ref"] not in rec["computational_plan_ids"]: rec["computational_plan_ids"].append(body["component_ref"]); rec["computational_plan_fingerprints"][body["component_ref"]]=fingerprint
        bid=_id("pbind-",{"component_type":body["component_type"],"component_ref":body["component_ref"],"workstream_id":body["workstream_id"],"role":body["role"]})
        item={"binding_id":bid,**body,"resolution_status":"resolved" if resolved else "declared-not-resolved-by-program-store","source_fingerprint":fingerprint,"human_recorded":True,"created_utc":_now()}
        if not any(x["binding_id"]==bid for x in rec["component_bindings"]): rec["component_bindings"].append(item); self._save(rec); self._event(pid,"component-binding.added",actor,{"binding_id":bid,"component_type":body["component_type"]})
        return self.get(pid)
    def add_milestone(self,pid,req:ResearchProgramMilestoneAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["workstream_ids"]=_uniq(body["workstream_ids"]); body["dependency_milestone_ids"]=_uniq(body["dependency_milestone_ids"]); body["required_binding_ids"]=_uniq(body["required_binding_ids"]); body["acceptance_criteria"]=_uniq(body["acceptance_criteria"])
        known_ws={x["workstream_id"] for x in rec["workstreams"]}; known_ms={x["milestone_id"] for x in rec["milestones"]}; known_bind={x["binding_id"] for x in rec["component_bindings"]}
        if any(x not in known_ws for x in body["workstream_ids"]): raise ValueError("Milestone references an unknown workstream_id.")
        if any(x not in known_ms for x in body["dependency_milestone_ids"]): raise ValueError("Milestone references an unknown dependency_milestone_id.")
        if any(x not in known_bind for x in body["required_binding_ids"]): raise ValueError("Milestone references an unknown required_binding_id.")
        mid=_id("milestone-",{"label":body["label"],"objective":body["objective"],"workstream_ids":body["workstream_ids"],"dependency_milestone_ids":body["dependency_milestone_ids"],"required_binding_ids":body["required_binding_ids"]})
        item={"milestone_id":mid,**body,"human_recorded":True,"completion_is_not_inferred":True,"created_utc":_now()}
        if not any(x["milestone_id"]==mid for x in rec["milestones"]): rec["milestones"].append(item); self._save(rec); self._event(pid,"milestone.added",actor,{"milestone_id":mid})
        return self.get(pid)
    def decide_milestone(self,pid,req:ResearchProgramMilestoneDecisionRequest):
        rec=self.get(pid)
        if req.milestone_id not in {x["milestone_id"] for x in rec["milestones"]}: raise ValueError("Milestone decision references an unknown milestone_id.")
        item={"milestone_id":req.milestone_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"human_recorded":True,"scientific_conclusion":False,"updated_utc":_now()}
        old=next((x for x in rec["milestone_decisions"] if x["milestone_id"]==req.milestone_id),None)
        if old: old.update(item)
        else: rec["milestone_decisions"].append(item)
        self._save(rec); self._event(pid,"milestone.decision",req.actor_ref,{"milestone_id":req.milestone_id,"decision":req.decision}); return self.get(pid)
    def add_deliverable(self,pid,req:ResearchProgramDeliverableAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["binding_ids"]=_uniq(body["binding_ids"])
        if body["milestone_id"] and body["milestone_id"] not in {x["milestone_id"] for x in rec["milestones"]}: raise ValueError("Deliverable references an unknown milestone_id.")
        if body["workstream_id"] and body["workstream_id"] not in {x["workstream_id"] for x in rec["workstreams"]}: raise ValueError("Deliverable references an unknown workstream_id.")
        known={x["binding_id"] for x in rec["component_bindings"]}
        if any(x not in known for x in body["binding_ids"]): raise ValueError("Deliverable references an unknown binding_id.")
        did=_id("deliverable-",{"label":body["label"],"deliverable_type":body["deliverable_type"],"milestone_id":body["milestone_id"],"workstream_id":body["workstream_id"],"binding_ids":body["binding_ids"]})
        item={"deliverable_id":did,**body,"human_recorded":True,"acceptance_is_not_inferred":True,"created_utc":_now()}
        if not any(x["deliverable_id"]==did for x in rec["deliverables"]): rec["deliverables"].append(item); self._save(rec); self._event(pid,"deliverable.added",actor,{"deliverable_id":did})
        return self.get(pid)
    def add_constraint(self,pid,req:ResearchProgramConstraintAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); cid=_id("pconstraint-",body); item={"constraint_id":cid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["constraint_id"]==cid for x in rec["constraints"]): rec["constraints"].append(item); self._save(rec); self._event(pid,"constraint.added",actor,{"constraint_id":cid})
        return self.get(pid)
    def set_state(self,pid,req:ResearchProgramStateRequest):
        rec=self.get(pid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(pid)
    def program_graph(self,pid):
        rec=self.get(pid); nodes=[]; edges=[]
        for ws in rec["workstreams"]:
            nodes.append({"node_id":ws["workstream_id"],"node_type":"workstream","label":ws["label"],"state":ws["state"]})
            for dep in ws["dependencies"]: edges.append({"from_node_id":dep,"to_node_id":ws["workstream_id"],"relation":"workstream-precedes"})
        for b in rec["component_bindings"]:
            nodes.append({"node_id":b["binding_id"],"node_type":"component-binding","label":b["component_type"],"state":b["resolution_status"]})
            if b.get("workstream_id"): edges.append({"from_node_id":b["binding_id"],"to_node_id":b["workstream_id"],"relation":"contributes-to"})
        for m in rec["milestones"]:
            nodes.append({"node_id":m["milestone_id"],"node_type":"milestone","label":m["label"],"state":next((x["decision"] for x in rec["milestone_decisions"] if x["milestone_id"]==m["milestone_id"]),"pending")})
            for dep in m["dependency_milestone_ids"]: edges.append({"from_node_id":dep,"to_node_id":m["milestone_id"],"relation":"milestone-precedes"})
            for wid in m["workstream_ids"]: edges.append({"from_node_id":wid,"to_node_id":m["milestone_id"],"relation":"advances"})
            for bid in m["required_binding_ids"]: edges.append({"from_node_id":bid,"to_node_id":m["milestone_id"],"relation":"required-for"})
        for d in rec["deliverables"]:
            nodes.append({"node_id":d["deliverable_id"],"node_type":"deliverable","label":d["label"],"state":d["state"]})
            if d.get("milestone_id"): edges.append({"from_node_id":d["milestone_id"],"to_node_id":d["deliverable_id"],"relation":"produces"})
            if d.get("workstream_id"): edges.append({"from_node_id":d["workstream_id"],"to_node_id":d["deliverable_id"],"relation":"owns"})
        graph={m["milestone_id"]:[] for m in rec["milestones"]}
        for m in rec["milestones"]:
            for dep in m["dependency_milestone_ids"]: graph.setdefault(dep,[]).append(m["milestone_id"])
        visiting=set(); visited=set(); cycle=False
        def dfs(x):
            nonlocal cycle
            if x in visiting: cycle=True; return
            if x in visited: return
            visiting.add(x)
            for y in graph.get(x,[]): dfs(y)
            visiting.remove(x); visited.add(x)
        for x in list(graph): dfs(x)
        return {"schema":RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA,"research_program_id":pid,"nodes":nodes,"edges":edges,"milestone_dependency_cycle":cycle,"governance":{"graph_is_declared_program_structure_not_execution_or_scientific_validity":True}}
    def portfolio_summary(self,pid):
        rec=self.get(pid); decisions={x["milestone_id"]:x["decision"] for x in rec["milestone_decisions"]}
        counts={state:sum(1 for x in rec["milestones"] if decisions.get(x["milestone_id"],"pending")==state) for state in ["pending","approved","completed","blocked","waived"]}
        return {"schema":RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA,"research_program_id":pid,"workstream_count":len(rec["workstreams"]),"binding_count":len(rec["component_bindings"]),"computational_plan_count":len(rec.get("computational_plan_ids",[])),"milestone_count":len(rec["milestones"]),"milestone_decision_counts":counts,"deliverable_count":len(rec["deliverables"]),"blocking_constraint_count":sum(1 for x in rec["constraints"] if x.get("blocking")),"governance":{"counts_are_descriptive_not_priority_or_quality_scores":True}}
    def readiness(self,pid):
        rec=self.get(pid); blockers=[]; decisions={x["milestone_id"]:x["decision"] for x in rec["milestone_decisions"]}
        if not rec["workstreams"]: blockers.append("no-workstreams")
        if not rec["component_bindings"]: blockers.append("no-component-bindings")
        if not rec["milestones"]: blockers.append("no-milestones")
        if rec["milestones"] and any(decisions.get(x["milestone_id"],"pending")=="pending" for x in rec["milestones"]): blockers.append("milestones-await-human-decision")
        if any(x.get("blocking") for x in rec["constraints"]): blockers.append("blocking-program-constraint")
        if self.program_graph(pid)["milestone_dependency_cycle"]: blockers.append("milestone-dependency-cycle")
        if rec["review"]["state"]!="approved": blockers.append("program-not-human-approved")
        return {"schema":RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA,"research_program_id":pid,"ready_for_program_handoff":not blockers,"blockers":blockers,"dimensions":{"workstreams_declared":bool(rec["workstreams"]),"components_bound":bool(rec["component_bindings"]),"milestones_declared":bool(rec["milestones"]),"program_human_approved":rec["review"]["state"]=="approved","dependency_graph_acyclic":not self.program_graph(pid)["milestone_dependency_cycle"]},"governance":{"readiness_is_program_structural_readiness_not_scientific_validity":True,"automatic_prioritization":False,"automatic_execution":False}}
    def handoffs(self,pid):
        rec=self.get(pid); ready=self.readiness(pid); packets=[]
        for ws in rec["workstreams"]:
            bindings=[x for x in rec["component_bindings"] if x.get("workstream_id")==ws["workstream_id"] or (x["component_type"]=="computational-research-plan" and x["component_ref"] in ws.get("computational_plan_ids",[]))]
            milestones=[x for x in rec["milestones"] if ws["workstream_id"] in x.get("workstream_ids",[])]
            packets.append({"schema":"sc-research-librarian-research-program-handoff/1.0","handoff_id":_id("proghand-",{"program":pid,"workstream":ws["workstream_id"]}),"research_program_id":pid,"workstream":ws,"component_bindings":bindings,"milestones":milestones,"handoff_ready":ready["ready_for_program_handoff"],"write_performed":False,"execution_performed":False,"resource_allocation_performed":False,"scientific_judgment_performed":False})
        return {"schema":RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA,"research_program_id":pid,"packets":packets,"governance":{"handoffs_are_coordination_packets_not_execution_orders":True,"specialist_runtime_execution_preserved":True}}
    def core_candidate(self,pid):
        rec=self.get(pid); ready=self.readiness(pid)
        return {"schema":"sc-research-librarian-core-research-program-candidate/1.0","candidate_id":_id("corecand-",{"research_program_id":pid,"type":"research-program"}),"object_type":"research-program","source_research_program_id":pid,"payload":{"title":rec["title"],"program_ref":rec["program_ref"],"mission":rec["mission"],"research_objectives":rec["research_objectives"],"workstreams":rec["workstreams"],"component_bindings":rec["component_bindings"],"milestones":rec["milestones"],"milestone_decisions":rec["milestone_decisions"],"deliverables":rec["deliverables"],"constraints":rec["constraints"]},"handoff_status":"human-approved-candidate" if ready["ready_for_program_handoff"] else "draft-candidate","promotion_performed":False,"execution_performed":False,"governance":{"platform_core_remains_authoritative":True,"candidate_is_not_promoted_object":True,"program_readiness_is_not_scientific_validity":True}}
    def freeze_snapshot(self,req:ResearchProgramSnapshotRequest):
        rec=self.get(req.research_program_id); payload={"schema":RESEARCH_PROGRAM_SNAPSHOT_SCHEMA,"research_program_id":req.research_program_id,"program":rec,"program_graph":self.program_graph(req.research_program_id),"portfolio_summary":self.portfolio_summary(req.research_program_id),"readiness":self.readiness(req.research_program_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_program_record_not_scientific_certification":True}}
        h=_sha(payload); sid="rprogsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_program_snapshots(snapshot_id,research_program_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.research_program_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO research_program_snapshots(snapshot_id,research_program_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.research_program_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.research_program_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA,"release":settings.release_version,"milestone":"11.0","durable":True,"workstream_registry":True,"component_binding_registry":True,"milestone_dependency_graph":True,"deliverable_registry":True,"program_level_lineage":True,"program_handoffs":True,"human_program_approval_required":True,"component_authority_remains_with_source_system":True,"specialist_runtimes_own_execution":True,"platform_core_remains_research_object_authority":True,"automatic_research_prioritization":False,"automatic_resource_allocation":False,"automatic_milestone_completion":False,"automatic_scientific_judgment":False,"automatic_execution":False,"automatic_truth_promotion":False}
_store=None
def get_research_program_intelligence_store():
    global _store
    if _store is None: _store=ResearchProgramIntelligenceStore()
    return _store
