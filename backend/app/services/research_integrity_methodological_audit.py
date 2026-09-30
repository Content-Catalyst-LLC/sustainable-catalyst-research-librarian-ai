from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator, Callable

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_integrity_methodological_audit import *

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None


def _json(v: Any) -> str: return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
def _sha(v: Any) -> str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _id(prefix: str, value: Any) -> str: return prefix + _sha(value)[:32]
def _uniq(values: list[str]) -> list[str]: return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))


class ResearchIntegrityMethodologicalAuditStore:
    def __init__(self, sqlite_path: Path | None = None, target_resolvers: dict[str, Callable[[str], dict[str, Any]]] | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "research_integrity_methodological_audit.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        self.target_resolvers = target_resolvers or {}
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres research-integrity audit storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._migrate_sqlite()

    def _default_resolver(self, target_type: str):
        try:
            if target_type == "research-question-plan":
                from .research_question_hypothesis import get_research_question_hypothesis_store
                return get_research_question_hypothesis_store().get
            if target_type == "research-design-plan":
                from .research_design_methodology import get_research_design_methodology_store
                return get_research_design_methodology_store().get
            if target_type == "evidence-search-strategy-plan":
                from .evidence_search_strategy import get_evidence_search_strategy_store
                return get_evidence_search_strategy_store().get
            if target_type == "systematic-review-plan":
                from .systematic_review_evidence_synthesis import get_systematic_review_evidence_synthesis_store
                return get_systematic_review_evidence_synthesis_store().get
            if target_type == "study-protocol":
                from .study_protocol_preregistration import get_study_protocol_preregistration_store
                return get_study_protocol_preregistration_store().get
            if target_type == "statistical-analysis-plan-intelligence":
                from .statistical_analysis_planning_intelligence import get_statistical_analysis_planning_intelligence_store
                return get_statistical_analysis_planning_intelligence_store().get
            if target_type == "causal-research-design":
                from .causal_research_design_intelligence import get_causal_research_design_intelligence_store
                return get_causal_research_design_intelligence_store().get
            if target_type == "simulation-model-study-plan":
                from .simulation_model_study_planner import get_simulation_model_study_planner_store
                return get_simulation_model_study_planner_store().get
            if target_type == "reproduction-replication-plan":
                from .reproduction_replication_intelligence import get_reproduction_replication_intelligence_store
                return get_reproduction_replication_intelligence_store().get
            if target_type == "cross-study-synthesis-plan":
                from .cross_study_synthesis_meta_research import get_cross_study_synthesis_meta_research_store
                return get_cross_study_synthesis_meta_research_store().get
        except Exception:
            return None
        return None

    def _resolve_target(self, item: dict[str, Any]) -> dict[str, Any]:
        typ = str(item.get("target_type") or "")
        ref = str(item.get("target_ref") or "")
        resolver = self.target_resolvers.get(typ) or self._default_resolver(typ)
        resolved_hash = str(item.get("source_hash") or "")
        resolved = False
        if resolver is not None:
            try:
                record = resolver(ref)
            except Exception as exc:
                raise ValueError(f"audit target is not available for {typ}: {ref}") from exc
            resolved_hash = str(record.get("record_hash") or record.get("snapshot_hash") or resolved_hash)
            resolved = True
        return {**item, "resolved": resolved, "resolved_hash": resolved_hash, "lineage_checked_utc": _now()}

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.sqlite_path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self, migration: bool = False):
        url = (settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self) -> None:
        with self._lock, self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS research_integrity_audits(audit_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_integrity_audit_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,audit_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_integrity_audit_snapshots(snapshot_id TEXT PRIMARY KEY,audit_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_research_integrity_audits(audit_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_integrity_audit_events(event_id BIGSERIAL PRIMARY KEY,audit_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_research_integrity_audit_events_audit ON sc_rl_research_integrity_audit_events(audit_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_integrity_audit_snapshots(snapshot_id TEXT PRIMARY KEY,audit_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]:
                c.execute(ddl)
            c.commit()

    def _event(self, audit_id: str, typ: str, actor: str, payload: dict[str, Any]) -> None:
        created = _now()
        h = _sha({"audit_id": audit_id, "event_type": typ, "actor_ref": actor, "payload": payload, "created_utc": created})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_research_integrity_audit_events(audit_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)", (audit_id, typ, actor, Jsonb(payload), h, created)); c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("INSERT INTO research_integrity_audit_events(audit_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)", (audit_id, typ, actor, _json(payload), h, created))

    def _save(self, rec: dict[str, Any]) -> dict[str, Any]:
        rec["updated_utc"] = _now()
        rec["record_hash"] = _sha({k:v for k,v in rec.items() if k != "record_hash"})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_research_integrity_audits(audit_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(audit_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc", (rec["audit_id"], Jsonb(rec), rec["record_hash"], rec["created_utc"], rec["updated_utc"])); c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("INSERT OR REPLACE INTO research_integrity_audits(audit_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)", (rec["audit_id"], _json(rec), rec["record_hash"], rec["created_utc"], rec["updated_utc"]))
        return rec

    def get(self, audit_id: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as c: row = c.execute("SELECT record FROM sc_rl_research_integrity_audits WHERE audit_id=%s", (audit_id,)).fetchone()
            if not row: raise ValueError("Research integrity audit not found.")
            return dict(row["record"])
        with self._lock, self._sqlite() as c: row = c.execute("SELECT record_json FROM research_integrity_audits WHERE audit_id=?", (audit_id,)).fetchone()
        if not row: raise ValueError("Research integrity audit not found.")
        return json.loads(row["record_json"])

    def create(self, req: ResearchIntegrityAuditCreateRequest) -> dict[str, Any]:
        body = req.model_dump(); actor = body.pop("actor_ref")
        targets = [self._resolve_target(x.model_dump() if hasattr(x, "model_dump") else dict(x)) for x in req.targets]
        body["targets"] = targets
        body["audit_standard_refs"] = _uniq(body.get("audit_standard_refs", []))
        aid = _id("riaudit-", {k:v for k,v in body.items() if k != "metadata"})
        try: return self.get(aid)
        except ValueError: pass
        rec = {
            "schema": RESEARCH_INTEGRITY_AUDIT_SCHEMA, "audit_id": aid, **body,
            "criteria": [], "observations": [], "findings": [], "methodological_appraisals": [],
            "verification_requests": [], "verification_receipts": [], "remediation_actions": [], "decisions": [],
            "review": {"state":"draft", "note":"", "actor_ref":actor, "updated_utc":_now()},
            "created_utc": _now(), "updated_utc": _now(),
            "governance": {
                "audit_findings_are_human_authored": True,
                "methodological_appraisals_are_human_authored": True,
                "discrepancies_are_review_signals_not_misconduct_findings": True,
                "specialist_runtimes_own_verification_execution": True,
                "platform_core_remains_governed_research_object_authority": True,
                "automatic_misconduct_inference": False,
                "automatic_invalidity_verdict": False,
                "automatic_retraction_recommendation": False,
                "automatic_methodological_scoring": False,
                "automatic_claim_rejection": False,
                "automatic_evidence_suppression": False,
                "automatic_causal_inference": False,
                "automatic_publication_block": False,
                "automatic_execution": False,
                "automatic_truth_promotion": False,
            },
        }
        self._save(rec); self._event(aid, "research-integrity-audit.created", actor, {"target_count":len(targets), "audit_scope":body["audit_scope"]})
        return self.get(aid)

    def _append(self, audit_id: str, key: str, id_key: str, prefix: str, body: dict[str, Any], event: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        rec = self.get(audit_id); actor = body.pop("actor_ref"); oid = _id(prefix, body)
        item = {id_key:oid, **body, **(extra or {}), "created_utc":_now()}
        if not any(x[id_key] == oid for x in rec[key]):
            rec[key].append(item); self._save(rec); self._event(audit_id, event, actor, {id_key:oid})
        return self.get(audit_id)

    def add_target(self, audit_id: str, req: ResearchIntegrityTargetAddRequest) -> dict[str, Any]:
        rec = self.get(audit_id); body=req.model_dump(); actor=body.pop("actor_ref"); item=self._resolve_target(body)
        if not any(x.get("target_type")==item["target_type"] and x.get("target_ref")==item["target_ref"] for x in rec["targets"]):
            rec["targets"].append(item); self._save(rec); self._event(audit_id,"audit-target.added",actor,{"target_type":item["target_type"],"target_ref":item["target_ref"]})
        return self.get(audit_id)

    def add_criterion(self, audit_id: str, req: ResearchIntegrityCriterionAddRequest) -> dict[str, Any]:
        return self._append(audit_id,"criteria","criterion_id","criterion-",req.model_dump(),"audit-criterion.added",{"human_authored":True})

    def add_observation(self, audit_id: str, req: ResearchIntegrityObservationAddRequest) -> dict[str, Any]:
        rec=self.get(audit_id)
        if req.criterion_id not in {x["criterion_id"] for x in rec["criteria"]}: raise ValueError("criterion_id is not registered in this audit.")
        return self._append(audit_id,"observations","observation_id","observation-",req.model_dump(),"audit-observation.added",{"human_authored":True,"status_is_review_signal_not_verdict":True})

    def add_finding(self, audit_id: str, req: ResearchIntegrityFindingAddRequest) -> dict[str, Any]:
        rec=self.get(audit_id)
        if req.criterion_id not in {x["criterion_id"] for x in rec["criteria"]}: raise ValueError("criterion_id is not registered in this audit.")
        return self._append(audit_id,"findings","finding_id","finding-",req.model_dump(),"audit-finding.added",{"human_authored":True,"disposition":"open","disposition_rationale":"","disposition_actor_ref":"","disposition_updated_utc":"","misconduct_not_inferred":True,"invalidity_not_inferred":True})

    def add_appraisal(self, audit_id: str, req: ResearchIntegrityMethodologicalAppraisalAddRequest) -> dict[str, Any]:
        return self._append(audit_id,"methodological_appraisals","appraisal_id","appraisal-",req.model_dump(),"methodological-appraisal.added",{"human_authored":True,"judgment_is_domain_scoped_not_global_validity":True})

    def add_verification_request(self, audit_id: str, req: ResearchIntegrityVerificationRequestAddRequest) -> dict[str, Any]:
        return self._append(audit_id,"verification_requests","verification_request_id","verify-",req.model_dump(),"verification-request.added",{"execution_performed":False})

    def _approved(self, rec: dict[str, Any], object_type: str, object_id: str) -> bool:
        ds=[x for x in rec.get("decisions",[]) if x.get("object_type")==object_type and x.get("object_id")==object_id]
        return bool(ds and ds[-1].get("decision") in {"approved","waived"})

    def add_verification_receipt(self, audit_id: str, req: ResearchIntegrityVerificationReceiptAddRequest) -> dict[str, Any]:
        rec=self.get(audit_id); ids={x["verification_request_id"] for x in rec["verification_requests"]}
        if req.verification_request_id not in ids: raise ValueError("verification_request_id is not registered in this audit.")
        if not self._approved(rec,"verification-request",req.verification_request_id): raise ValueError("verification request requires human approval before an execution receipt can be attached.")
        return self._append(audit_id,"verification_receipts","verification_receipt_id","verifyreceipt-",req.model_dump(),"verification-receipt.added",{"receipt_is_observation_not_integrity_verdict":True,"automatic_finding_creation":False})

    def add_remediation_action(self, audit_id: str, req: ResearchIntegrityRemediationActionAddRequest) -> dict[str, Any]:
        rec=self.get(audit_id); known={x["finding_id"] for x in rec["findings"]}; missing=[x for x in req.finding_ids if x not in known]
        if missing: raise ValueError("remediation action references unknown finding_id: " + ", ".join(missing))
        body=req.model_dump(); body["finding_ids"]=_uniq(body["finding_ids"])
        return self._append(audit_id,"remediation_actions","remediation_action_id","remediation-",body,"remediation-action.added",{"status":"planned","status_note":"","status_actor_ref":"","status_updated_utc":""})

    def set_remediation_status(self, audit_id: str, req: ResearchIntegrityRemediationStatusRequest) -> dict[str, Any]:
        rec=self.get(audit_id); found=False
        for item in rec["remediation_actions"]:
            if item["remediation_action_id"]==req.remediation_action_id:
                item.update({"status":req.status,"status_note":req.note,"status_actor_ref":req.actor_ref,"status_updated_utc":_now()}); found=True; break
        if not found: raise ValueError("remediation_action_id is not registered in this audit.")
        self._save(rec); self._event(audit_id,"remediation-action.status",req.actor_ref,{"remediation_action_id":req.remediation_action_id,"status":req.status}); return self.get(audit_id)

    def set_finding_disposition(self, audit_id: str, req: ResearchIntegrityFindingDispositionRequest) -> dict[str, Any]:
        rec=self.get(audit_id); found=False
        for item in rec["findings"]:
            if item["finding_id"]==req.finding_id:
                item.update({"disposition":req.disposition,"disposition_rationale":req.rationale,"disposition_actor_ref":req.actor_ref,"disposition_updated_utc":_now()}); found=True; break
        if not found: raise ValueError("finding_id is not registered in this audit.")
        self._save(rec); self._event(audit_id,"audit-finding.disposition",req.actor_ref,{"finding_id":req.finding_id,"disposition":req.disposition}); return self.get(audit_id)

    def decide(self, audit_id: str, req: ResearchIntegrityDecisionRequest) -> dict[str, Any]:
        rec=self.get(audit_id)
        mapping={
            "criterion":("criteria","criterion_id"), "finding":("findings","finding_id"), "appraisal":("methodological_appraisals","appraisal_id"),
            "verification-request":("verification_requests","verification_request_id"), "remediation-action":("remediation_actions","remediation_action_id"),
        }
        key,id_key=mapping[req.object_type]
        if req.object_id not in {x[id_key] for x in rec[key]}: raise ValueError(f"{req.object_type} object is not registered in this audit.")
        item={"decision_id":_id("auditdecision-",req.model_dump()),**req.model_dump(),"human_authored":True,"created_utc":_now()}
        if not any(x["decision_id"]==item["decision_id"] for x in rec["decisions"]):
            rec["decisions"].append(item); self._save(rec); self._event(audit_id,"human-decision.recorded",req.actor_ref,{"decision_id":item["decision_id"],"decision":req.decision})
        return self.get(audit_id)

    def set_state(self, audit_id: str, req: ResearchIntegrityAuditStateRequest) -> dict[str, Any]:
        rec=self.get(audit_id); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(audit_id,"audit.state",req.actor_ref,{"state":req.state}); return self.get(audit_id)

    def traceability_matrix(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id); rows=[]
        obs_by={}
        for x in rec["observations"]: obs_by.setdefault(x["criterion_id"],[]).append(x)
        find_by={}
        for x in rec["findings"]: find_by.setdefault(x["criterion_id"],[]).append(x)
        for c in rec["criteria"]:
            rows.append({"criterion":c,"observations":obs_by.get(c["criterion_id"],[]),"findings":find_by.get(c["criterion_id"],[])})
        return {"schema":RESEARCH_INTEGRITY_AUDIT_SCHEMA,"audit_id":audit_id,"targets":rec["targets"],"rows":rows,"governance":{"traceability_is_documented_lineage_not_automated_integrity_judgment":True}}

    def discrepancy_register(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id)
        observations=[x for x in rec["observations"] if x.get("status") in {"inconsistent","unclear"}]
        findings=[x for x in rec["findings"] if x.get("disposition")=="open"]
        return {"schema":RESEARCH_INTEGRITY_AUDIT_SCHEMA,"audit_id":audit_id,"observations":observations,"open_findings":findings,"governance":{"discrepancy_is_review_signal_not_misconduct_or_invalidity_verdict":True}}

    def methodological_profile(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id); by={}
        for x in rec["methodological_appraisals"]: by.setdefault(x["domain"],[]).append(x)
        return {"schema":RESEARCH_INTEGRITY_AUDIT_SCHEMA,"audit_id":audit_id,"domains":by,"governance":{"no_composite_quality_score":True,"no_methodological_ranking":True,"human_judgments_remain_attributed":True}}

    def verification_handoffs(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id); packets=[]
        for r in rec["verification_requests"]:
            if not self._approved(rec,"verification-request",r["verification_request_id"]): continue
            packets.append({"schema":"sc-research-librarian-integrity-verification-handoff/1.0","handoff_id":_id("integrityhandoff-",{"audit_id":audit_id,"verification_request_id":r["verification_request_id"]}),"audit_id":audit_id,"verification_request":r,"targets":rec["targets"],"target":r.get("runtime_target") or "workspace","execution_performed":False,"finding_created":False,"misconduct_inferred":False,"truth_promoted":False})
        return {"audit_id":audit_id,"packets":packets,"governance":{"specialist_runtime_executes":True,"librarian_does_not_execute_verification":True}}

    def remediation_status(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id); counts={}
        for x in rec["remediation_actions"]: counts[x.get("status","planned")]=counts.get(x.get("status","planned"),0)+1
        open_findings=[x for x in rec["findings"] if x.get("disposition")=="open"]
        return {"schema":RESEARCH_INTEGRITY_AUDIT_SCHEMA,"audit_id":audit_id,"action_counts":counts,"open_finding_count":len(open_findings),"actions":rec["remediation_actions"],"governance":{"completion_status_does_not_certify_research_validity":True}}

    def readiness(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id); blockers=[]
        if not rec["targets"]: blockers.append("no-audit-targets")
        if not rec["criteria"]: blockers.append("no-audit-criteria")
        if not rec["observations"] and not rec["findings"] and not rec["methodological_appraisals"]: blockers.append("no-audit-evidence-or-appraisal")
        unresolved=[x for x in rec["targets"] if not x.get("resolved") and not x.get("resolved_hash")]
        return {"schema":RESEARCH_INTEGRITY_AUDIT_SCHEMA,"audit_id":audit_id,"ready_for_human_review":not blockers,"blockers":blockers,"unresolved_external_target_count":len(unresolved),"governance":{"readiness_is_structural_not_integrity_or_validity_certification":True,"human_review_required":True}}

    def core_candidate(self, audit_id: str) -> dict[str, Any]:
        rec=self.get(audit_id)
        return {"schema":"sc-research-librarian-core-candidate/1.0","object_type":"research-integrity-methodological-audit","source_id":audit_id,"source_hash":rec["record_hash"],"payload":{"audit":rec,"traceability_matrix":self.traceability_matrix(audit_id),"discrepancy_register":self.discrepancy_register(audit_id),"methodological_profile":self.methodological_profile(audit_id),"remediation_status":self.remediation_status(audit_id)},"requires_core_governance":True,"misconduct_not_inferred":True,"scientific_validity_not_certified":True,"truth_promoted":False}

    def freeze_snapshot(self, req: ResearchIntegrityAuditSnapshotRequest) -> dict[str, Any]:
        rec=self.get(req.audit_id)
        payload={"schema":RESEARCH_INTEGRITY_AUDIT_SNAPSHOT_SCHEMA,"audit_id":req.audit_id,"record":rec,"traceability_matrix":self.traceability_matrix(req.audit_id),"discrepancy_register":self.discrepancy_register(req.audit_id),"methodological_profile":self.methodological_profile(req.audit_id),"remediation_status":self.remediation_status(req.audit_id),"readiness":self.readiness(req.audit_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_audit_record_not_misconduct_or_validity_certification":True}}
        h=_sha(payload); sid="riauditsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_integrity_audit_snapshots(snapshot_id,audit_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.audit_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO research_integrity_audit_snapshots(snapshot_id,audit_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.audit_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.audit_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload


def capabilities() -> dict[str, Any]:
    return {
        "schema": RESEARCH_INTEGRITY_AUDIT_SCHEMA, "release": settings.release_version, "milestone": "11.7", "durable": True,
        "declared_method_lineage": True, "human_audit_criteria": True, "protocol_report_consistency_observations": True,
        "human_integrity_findings": True, "human_methodological_appraisals": True, "specialist_verification_handoffs": True,
        "verification_receipts": True, "remediation_tracking": True, "traceability_matrix": True, "discrepancy_register": True,
        "methodological_profile_without_score": True, "core_candidate": True, "immutable_snapshot": True,
        "audit_findings_are_human_authored": True, "specialist_runtimes_own_verification_execution": True,
        "platform_core_remains_governed_research_object_authority": True,
        "automatic_misconduct_inference": False, "automatic_invalidity_verdict": False,
        "automatic_retraction_recommendation": False, "automatic_methodological_scoring": False,
        "automatic_claim_rejection": False, "automatic_evidence_suppression": False,
        "automatic_causal_inference": False, "automatic_publication_block": False,
        "automatic_execution": False, "automatic_truth_promotion": False,
    }


_store: ResearchIntegrityMethodologicalAuditStore | None = None
def get_research_integrity_methodological_audit_store() -> ResearchIntegrityMethodologicalAuditStore:
    global _store
    if _store is None: _store = ResearchIntegrityMethodologicalAuditStore()
    return _store
