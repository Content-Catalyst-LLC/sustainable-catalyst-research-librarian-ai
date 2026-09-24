from __future__ import annotations

import hashlib
import json
from typing import Any

from ..clients.platform_core import PlatformCoreClient
from ..config import settings
from ..contracts.unified_research_runtime import (
    CORE_UNIFIED_RESEARCH_CONTRACT,
    UNIFIED_RESEARCH_RUNTIME_SCHEMA,
    UnifiedResearchRuntimeExecutionRequest,
    UnifiedResearchRuntimePlan,
    UnifiedResearchRuntimePlanRequest,
)
from ..advanced_retrieval import build_query_plan
from .argument_synthesis import build_plan as build_argument_plan
from .core_research_sync import build_project_sync_plan
from .platform_core_integration import integration_readiness
from .research_intelligence_extraction import extract_candidates
from .statistical_research import build_plan as build_statistical_plan
from .visual_research import build_plan as build_visual_plan


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


_STAGE_CATALOG: dict[str, dict[str, Any]] = {
    "discovery": {"owner":"research-librarian", "mode":"read-only", "depends_on":[], "gate":None, "output":"research-path-and-source-candidates"},
    "ingestion": {"owner":"research-librarian", "mode":"durable-local-write", "depends_on":["discovery"], "gate":"explicit-source-selection", "output":"ingested-document-records"},
    "document-intelligence": {"owner":"research-librarian", "mode":"local-compute", "depends_on":["ingestion"], "gate":None, "output":"structured-scholarly-document"},
    "source-identity": {"owner":"research-librarian", "mode":"durable-local-write", "depends_on":["document-intelligence"], "gate":None, "output":"canonical-source-and-citation-graph"},
    "retrieval": {"owner":"research-librarian", "mode":"read-only", "depends_on":["source-identity"], "gate":None, "output":"ranked-evidence-candidates"},
    "evidence-governance": {"owner":"platform-core", "mode":"human-gated-core-write", "depends_on":["retrieval"], "gate":"explicit-evidence-promotion", "output":"governed-core-evidence"},
    "research-intelligence": {"owner":"research-librarian+platform-core", "mode":"local-compute-then-human-gated-core-write", "depends_on":["evidence-governance"], "gate":"candidate-review", "output":"reviewed-findings-and-claims"},
    "argument-synthesis": {"owner":"research-librarian+platform-core", "mode":"local-plan-then-human-gated-core-write", "depends_on":["research-intelligence"], "gate":"argument-review", "output":"governed-argument-and-open-tensions"},
    "statistical-analysis": {"owner":"specialist-runtime+platform-core", "mode":"external-compute-then-human-gated-core-write", "depends_on":["evidence-governance"], "gate":"analysis-plan-and-result-review", "output":"governed-statistical-reasoning"},
    "visual-research": {"owner":"research-librarian+platform-core+specialist-renderer", "mode":"local-plan-then-human-gated-core-write", "depends_on":["research-intelligence","statistical-analysis"], "gate":"visual-plan-review", "output":"governed-renderer-neutral-visual-object"},
    "project-state": {"owner":"platform-core", "mode":"explicit-core-state-version", "depends_on":["research-intelligence","argument-synthesis","statistical-analysis","visual-research"], "gate":"explicit-project-sync", "output":"immutable-project-state-version"},
    "reproducibility": {"owner":"platform-core", "mode":"core-reproducibility-package", "depends_on":["project-state"], "gate":"explicit-freeze-or-package", "output":"reproducible-research-package"},
}

_ENDPOINTS = {
    "discovery": "/v1/ask",
    "ingestion": "/v1/jobs/documents",
    "document-intelligence": "/v1/documents/parse",
    "source-identity": "/v1/sources/resolve",
    "retrieval": "/v1/retrieve/explain",
    "evidence-governance": "/v1/core/evidence",
    "research-intelligence": "/v1/core/research-intelligence/extract",
    "argument-synthesis": "/v1/core/argument-synthesis/plan",
    "statistical-analysis": "/v1/core/statistical-research/plan",
    "visual-research": "/v1/core/visual-research/plan",
    "project-state": "/v1/core/research-sync/plan",
    "reproducibility": "/v1/core/readiness",
}


def capabilities() -> dict[str, Any]:
    return {
        "schema": UNIFIED_RESEARCH_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "platform_core_contract": CORE_UNIFIED_RESEARCH_CONTRACT,
        "stage_catalog": _STAGE_CATALOG,
        "durable_async_runtime": True,
        "safe_local_stage_execution": True,
        "cross_stage_reproducibility_fingerprint": True,
        "explicit_human_review_gates": True,
        "automatic_core_writes": False,
        "automatic_truth_promotion": False,
        "automatic_claim_acceptance": False,
        "automatic_argument_resolution": False,
        "automatic_statistical_interpretation": False,
        "automatic_visual_inference": False,
        "specialist_computation_retained": True,
    }


def build_runtime_plan(request: UnifiedResearchRuntimePlanRequest) -> dict[str, Any]:
    raw = request.model_dump(mode="json", exclude_none=True)
    run_id = "rl-unified-run-" + _sha(raw)[:24]
    requested = list(request.requested_stages)
    stages: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    requested_set = set(requested)
    for index, name in enumerate(requested, 1):
        spec = dict(_STAGE_CATALOG[name])
        missing_dependencies = [x for x in spec["depends_on"] if x not in requested_set]
        status = "planned" if not missing_dependencies else "dependency-external"
        if name == "ingestion" and not request.document_refs:
            status = "awaiting-input"
        elif name == "source-identity" and not (request.document_refs or request.source_refs):
            status = "awaiting-input"
        elif name == "evidence-governance" and not request.core_evidence_refs:
            status = "human-gate"
        elif name in {"research-intelligence", "argument-synthesis", "project-state", "reproducibility"}:
            status = "human-gate-or-stage-payload"
        elif name == "statistical-analysis":
            status = "specialist-runtime-required"
        elif name == "visual-research":
            status = "visual-plan-required"
        stage = {
            "sequence": index,
            "stage": name,
            **spec,
            "status": status,
            "missing_dependencies": missing_dependencies,
            "endpoint": _ENDPOINTS[name],
        }
        stages.append(stage)
        if spec.get("gate"):
            gates.append({"stage": name, "gate": spec["gate"], "satisfied": False, "automatic": False})

    inputs = {
        "document_refs": list(request.document_refs),
        "source_refs": list(request.source_refs),
        "core_evidence_refs": list(request.core_evidence_refs),
        "core_research_object_refs": list(request.core_research_object_refs),
        "statistical_reasoning_refs": list(request.statistical_reasoning_refs),
        "visual_refs": list(request.visual_refs),
        "source_content_hashes": dict(request.source_content_hashes),
    }
    reproducibility_seed = {
        "run_id": run_id,
        "question": request.research_question,
        "objective": request.objective,
        "stages": requested,
        "inputs": inputs,
        "core_project_id": request.core_project_id,
        "local_project_id": request.local_project_id,
    }
    plan = UnifiedResearchRuntimePlan(
        run_id=run_id,
        core_project_id=request.core_project_id,
        core_session_id=request.core_session_id,
        local_project_id=request.local_project_id,
        title=request.title,
        research_question=request.research_question,
        objective=request.objective,
        stages=stages,
        stage_order=requested,
        inputs=inputs,
        gates=gates,
        endpoint_map={name:_ENDPOINTS[name] for name in requested},
        reproducibility={
            "plan_hash": _sha(reproducibility_seed),
            "source_content_hashes": dict(request.source_content_hashes),
            "deterministic_stage_order": True,
            "immutable_core_state_expected": True,
            "run_manifest_schema": UNIFIED_RESEARCH_RUNTIME_SCHEMA,
        },
        governance={
            "research_librarian_orchestrates": True,
            "platform_core_governs_promoted_objects": True,
            "specialist_runtimes_compute": True,
            "human_review_required_for_core_promotion": True,
            "core_write_performed_by_unified_execute": False,
            "truth_determined": False,
        },
    )
    return {"schema":UNIFIED_RESEARCH_RUNTIME_SCHEMA, "release":settings.release_version, "plan":plan.model_dump(mode="json", exclude_none=True), "capabilities":capabilities()}


async def readiness(core: PlatformCoreClient | None = None) -> dict[str, Any]:
    client = core or PlatformCoreClient()
    integration = await integration_readiness(client)
    caps = integration.get("capabilities") if isinstance(integration, dict) else {}
    required = [
        "research_objects", "unified_research_projects", "research_lineage", "research_arguments",
        "reproducible_research", "statistical_reasoning", "visual_reasoning_objects",
        "unified_visual_reasoning", "project_state", "finding_claim_evidence_intelligence",
    ]
    missing = [name for name in required if not isinstance(caps, dict) or not (caps.get(name) or {}).get("ok")]
    return {
        "schema": UNIFIED_RESEARCH_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "ready": bool(integration.get("ok")) and not missing,
        "core_compatible": bool(integration.get("compatible")),
        "core_write_ready": bool(integration.get("write_ready")),
        "required_core_capabilities": required,
        "missing_or_failed_core_capabilities": missing,
        "integration": integration,
        "governance": capabilities(),
    }


def _completed_result(stage: str, result: dict[str, Any]) -> dict[str, Any]:
    return {"stage":stage, "status":"completed", "result":result, "result_hash":_sha(result), "core_write":False}


def execute_safe_runtime(request: UnifiedResearchRuntimeExecutionRequest) -> dict[str, Any]:
    requested = set(request.execute_stages)
    payloads = request.payloads
    results: dict[str, Any] = {}

    if "retrieval" in requested:
        results["retrieval"] = _completed_result("retrieval", {"query_plan": build_query_plan(request.plan.research_question)})

    if "research-intelligence" in requested:
        if payloads.research_intelligence is None:
            results["research-intelligence"] = {"stage":"research-intelligence","status":"awaiting-input","required":"payloads.research_intelligence","core_write":False}
        else:
            results["research-intelligence"] = _completed_result("research-intelligence", extract_candidates(payloads.research_intelligence))
            results["research-intelligence"]["next_gate"] = "candidate-review-before-core-promotion"

    if "argument-synthesis" in requested:
        if payloads.argument_synthesis is None:
            results["argument-synthesis"] = {"stage":"argument-synthesis","status":"awaiting-input","required":"payloads.argument_synthesis","core_write":False}
        else:
            results["argument-synthesis"] = _completed_result("argument-synthesis", build_argument_plan(payloads.argument_synthesis))
            results["argument-synthesis"]["next_gate"] = "argument-review-before-core-promotion"

    if "statistical-analysis" in requested:
        if payloads.statistical_analysis is None:
            results["statistical-analysis"] = {"stage":"statistical-analysis","status":"awaiting-input","required":"payloads.statistical_analysis","core_write":False}
        else:
            results["statistical-analysis"] = _completed_result("statistical-analysis", build_statistical_plan(payloads.statistical_analysis))
            results["statistical-analysis"]["next_gate"] = "specialist-runtime-execution-and-human-result-review"

    if "visual-research" in requested:
        if payloads.visual_research is None:
            results["visual-research"] = {"stage":"visual-research","status":"awaiting-input","required":"payloads.visual_research","core_write":False}
        else:
            results["visual-research"] = _completed_result("visual-research", build_visual_plan(payloads.visual_research))
            results["visual-research"]["next_gate"] = "visual-plan-review-before-core-promotion"

    if "project-state" in requested:
        if payloads.project_sync is None:
            results["project-state"] = {"stage":"project-state","status":"awaiting-input","required":"payloads.project_sync","core_write":False}
        else:
            results["project-state"] = _completed_result("project-state", build_project_sync_plan(payloads.project_sync))
            results["project-state"]["next_gate"] = "explicit-project-state-synchronization"

    manifest = {
        "run_id": request.plan.run_id,
        "plan_hash": request.plan.reproducibility.get("plan_hash"),
        "stage_result_hashes": {k:v.get("result_hash") for k,v in results.items() if v.get("result_hash")},
        "executed_stages": list(results),
        "core_writes_performed": False,
        "human_review_gates_preserved": True,
    }
    manifest["run_fingerprint"] = _sha(manifest)
    return {
        "schema": UNIFIED_RESEARCH_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "run_id": request.plan.run_id,
        "stage_results": results,
        "run_manifest": manifest,
        "next_actions": [
            "review candidate findings/claims before Core promotion",
            "review argument plan before Core promotion",
            "execute approved statistical plans only in a declared specialist runtime",
            "review visual plan before Core visual promotion",
            "synchronize/freeze project state explicitly when research state is ready",
        ],
        "governance": {
            "safe_execution_only": True,
            "automatic_core_writes": False,
            "automatic_truth_promotion": False,
            "automatic_claim_acceptance": False,
            "automatic_argument_resolution": False,
            "automatic_statistical_interpretation": False,
            "automatic_visual_inference": False,
        },
    }
