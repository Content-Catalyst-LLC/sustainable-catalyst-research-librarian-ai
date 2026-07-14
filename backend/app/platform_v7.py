from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
import uuid

from .models import utc_now

PROJECT_SCHEMA = "sc-research-project/1.0"
INVESTIGATION_SCHEMA = "sc-research-investigation/1.0"
EVIDENCE_COLLECTION_SCHEMA = "sc-evidence-collection/1.0"
READING_PATH_SCHEMA = "sc-annotated-reading-path/1.0"
WORKFLOW_SCHEMA = "sc-research-workflow/1.0"
UNCERTAINTY_SCHEMA = "sc-uncertainty-register/1.0"
BACKUP_SCHEMA = "sc-connected-research-backup/1.0"
API_SCHEMA = "sc-connected-research-api/1.0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def normalize_project(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = utc_now()
    title = str(payload.get("title") or existing.get("title") or "Untitled research project").strip()[:240]
    objective = str(payload.get("objective") or existing.get("objective") or "").strip()[:4000]
    project = {
        "schema": PROJECT_SCHEMA,
        "project_id": str(payload.get("project_id") or existing.get("project_id") or new_id("project"))[:220],
        "title": title,
        "objective": objective,
        "status": str(payload.get("status") or existing.get("status") or "active")[:60],
        "visibility": str(payload.get("visibility") or existing.get("visibility") or "private")[:40],
        "tags": [str(v).strip()[:100] for v in (payload.get("tags") or existing.get("tags") or []) if str(v).strip()][:30],
        "created_utc": str(existing.get("created_utc") or payload.get("created_utc") or now),
        "updated_utc": now,
        "owner_ref": str(payload.get("owner_ref") or existing.get("owner_ref") or "")[:220],
        "governance": dict(payload.get("governance") or existing.get("governance") or {"human_control": True, "publication_requires_review": True}),
    }
    project["fingerprint"] = fingerprint({k:v for k,v in project.items() if k!="fingerprint"})
    return project


def normalize_investigation(payload: dict[str, Any], project_id: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now=utc_now()
    inv={
        "schema":INVESTIGATION_SCHEMA,
        "investigation_id":str(payload.get("investigation_id") or existing.get("investigation_id") or new_id("investigation"))[:220],
        "project_id":project_id,
        "title":str(payload.get("title") or existing.get("title") or "Research investigation").strip()[:240],
        "question":str(payload.get("question") or existing.get("question") or "").strip()[:4000],
        "status":str(payload.get("status") or existing.get("status") or "open")[:60],
        "steps":list(payload.get("steps") or existing.get("steps") or [] )[:100],
        "evidence_collection_ids":list(payload.get("evidence_collection_ids") or existing.get("evidence_collection_ids") or [])[:100],
        "reading_path_ids":list(payload.get("reading_path_ids") or existing.get("reading_path_ids") or [])[:50],
        "workflow_ids":list(payload.get("workflow_ids") or existing.get("workflow_ids") or [])[:50],
        "artifact_ids":list(payload.get("artifact_ids") or existing.get("artifact_ids") or [])[:200],
        "created_utc":str(existing.get("created_utc") or payload.get("created_utc") or now),
        "updated_utc":now,
    }
    inv["fingerprint"]=fingerprint({k:v for k,v in inv.items() if k!="fingerprint"})
    return inv


def contradiction_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str,list[dict[str,Any]]]={}
    for item in items:
        claim=str(item.get("claim") or "").strip()
        if not claim: continue
        key=str(item.get("claim_key") or hashlib.sha256(claim.lower().encode()).hexdigest()[:16])
        groups.setdefault(key,[]).append(item)
    conflicts=[]
    for key, group in groups.items():
        positions={str(x.get("position") or "supports").lower() for x in group}
        if len(positions)>1 and ({"supports","opposes"} <= positions or "disputes" in positions):
            conflicts.append({"claim_key":key,"claim":group[0].get("claim",""),"positions":sorted(positions),"evidence":group})
    return {"schema":"sc-contradiction-report/1.0","conflict_count":len(conflicts),"conflicts":conflicts,"generated_utc":utc_now()}


def uncertainty_register(items: list[dict[str, Any]]) -> dict[str, Any]:
    rows=[]
    for item in items[:200]:
        likelihood=max(0.0,min(1.0,float(item.get("likelihood",0.5))))
        impact=max(0.0,min(1.0,float(item.get("impact",0.5))))
        rows.append({"uncertainty_id":str(item.get("uncertainty_id") or new_id("uncertainty")),"statement":str(item.get("statement") or "")[:1000],"likelihood":likelihood,"impact":impact,"priority":round(likelihood*impact,4),"status":str(item.get("status") or "open")[:60],"evidence_ids":list(item.get("evidence_ids") or [])[:50]})
    rows.sort(key=lambda x:x["priority"],reverse=True)
    return {"schema":UNCERTAINTY_SCHEMA,"items":rows,"count":len(rows),"generated_utc":utc_now()}


def workflow_template(kind: str, title: str = "") -> dict[str, Any]:
    templates={
        "evidence-review":["frame-question","collect-sources","compare-claims","record-uncertainty","human-review"],
        "site-intelligence":["frame-place","select-indicators","validate-sources","prepare-handoff","review-artifact"],
        "workbench-analysis":["extract-variables","state-assumptions","prepare-calculation","validate-output","attach-artifact"],
        "decision-packet":["define-decision","collect-evidence","compare-alternatives","document-uncertainty","prepare-decision-studio"],
        "lab-investigation":["state-hypothesis","define-method","prepare-instruments","run-validation","preserve-results"],
    }
    selected=templates.get(kind,templates["evidence-review"])
    return {"schema":WORKFLOW_SCHEMA,"workflow_id":new_id("workflow"),"kind":kind,"title":title or kind.replace("-"," ").title(),"steps":[{"step_id":f"step-{i+1}","type":v,"status":"pending","human_confirmation":True} for i,v in enumerate(selected)],"created_utc":utc_now(),"provider_boundary":{"retrieval":"provider-independent","generation":"adapter","fallback":"deterministic"}}


def backup_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    body={"schema":BACKUP_SCHEMA,"created_utc":utc_now(),"api_schema":API_SCHEMA,"payload":payload}
    body["checksum"]=fingerprint(body["payload"])
    return body


def verify_backup(envelope: dict[str, Any]) -> dict[str, Any]:
    expected=str(envelope.get("checksum") or "")
    actual=fingerprint(envelope.get("payload") or {})
    return {"ok":bool(expected and expected==actual),"expected":expected,"actual":actual,"schema":envelope.get("schema","")}
