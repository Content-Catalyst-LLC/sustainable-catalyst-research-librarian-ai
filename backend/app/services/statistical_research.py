from __future__ import annotations
import hashlib, json
from typing import Any
from ..clients.platform_core import PlatformCoreClient
from ..config import settings
from ..contracts.statistical_research import (
    STATISTICAL_RESEARCH_SCHEMA, CORE_STATISTICAL_CONTRACT, ANALYTICS_R_SOURCE_CONTRACT,
    StatisticalAnalysisPlan, StatisticalAnalysisPlanRequest, CoreStatisticalValidationPromotionRequest,
    CoreCoefficientRequest, CoreIntervalRequest, CoreInterpretationRequest,
)

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def capabilities()->dict[str,Any]:
    return {
        "schema":STATISTICAL_RESEARCH_SCHEMA,"release":settings.release_version,
        "core_contract":CORE_STATISTICAL_CONTRACT,"analytics_r_source_contract":ANALYTICS_R_SOURCE_CONTRACT,
        "analysis_planning":True,"specialist_runtime_handoff":True,"core_statistical_reasoning_registration":True,
        "assumption_and_diagnostic_provenance":True,"coefficient_and_interval_registration":True,
        "human_authored_interpretations":True,"immutable_core_reasoning_snapshots":True,
        "human_review_required_for_core_ingest":True,
        "librarian_executes_arbitrary_analysis":False,"core_executes_analysis":False,
        "automatic_significance_inference":False,"automatic_causality_inference":False,
        "automatic_model_ranking":False,"automatic_scientific_validity_certification":False,
        "automatic_truth_determination":False,
    }

def build_plan(request:StatisticalAnalysisPlanRequest)->dict[str,Any]:
    raw=request.model_dump(mode="json",exclude_none=True)
    plan_id="rl-stat-plan-"+_hash(raw)[:24]
    datasets=[]
    for i,d in enumerate(request.datasets,1):
        x=d.model_dump(mode="json",exclude_none=True)
        x["binding_key"]="rl-stat-dataset-"+_hash({"plan":plan_id,"ref":d.local_ref})[:24]
        x["sequence"]=i
        datasets.append(x)
    assumptions=[]
    for a in request.assumptions:
        x=a.model_dump(mode="json",exclude_none=True)
        x["researcher_declared"]=True
        assumptions.append(x)
    plan=StatisticalAnalysisPlan(
        plan_id=plan_id,core_project_id=request.core_project_id,title=request.title,
        research_question=request.research_question,runtime_target=request.runtime_target,
        analysis_type=request.analysis_type,datasets=datasets,methods=list(request.methods),
        assumptions=assumptions,requested_outputs=list(request.requested_outputs),
        evidence_refs=list(request.evidence_refs),limitations=list(request.limitations),
        execution_policy={"execution_allowed_in_librarian":False,"runtime_must_return_validated_bundle":True,
                          "preferred_source_contract":ANALYTICS_R_SOURCE_CONTRACT,
                          "core_executes_analysis":False,"human_review_before_core_ingest":True},
        provenance={"librarian_release":settings.release_version,"core_contract":CORE_STATISTICAL_CONTRACT,
                    "analysis_executed_by_librarian":False,"statistical_significance_inferred":False,
                    "causality_inferred":False,"truth_determined":False},
    )
    return {"schema":STATISTICAL_RESEARCH_SCHEMA,"release":settings.release_version,
            "core_contract":CORE_STATISTICAL_CONTRACT,"plan":plan.model_dump(mode="json",exclude_none=True),
            "governance":capabilities()}

async def readiness(core:PlatformCoreClient|None=None)->dict[str,Any]:
    client=core or PlatformCoreClient(); data=await client.statistical_reasoning_readiness()
    return {"schema":STATISTICAL_RESEARCH_SCHEMA,"release":settings.release_version,"core":data,
            "compatible_contract":data.get("contract")==CORE_STATISTICAL_CONTRACT,
            "execution_boundary":"specialist-runtime-only"}

async def promote_validation(request:CoreStatisticalValidationPromotionRequest,core:PlatformCoreClient|None=None)->dict[str,Any]:
    client=core or PlatformCoreClient()
    payload={"result_ref":request.result_ref,"evidence":dict(request.validation_evidence),
             "visibility":request.visibility,
             "reasoning_ref":request.reasoning_ref or f"statistical-reasoning:{request.plan.plan_id}"}
    result=await client.ingest_statistical_validation(payload)
    return {"schema":STATISTICAL_RESEARCH_SCHEMA,"release":settings.release_version,
            "plan_id":request.plan.plan_id,"reviewer_ref":request.plan.reviewer_ref,"core":result,
            "governance":{"human_reviewed":True,"analysis_executed_by_librarian":False,
                          "core_certifies_scientific_validity":False,"core_infers_statistical_significance":False}}

async def add_coefficient(request:CoreCoefficientRequest,core:PlatformCoreClient|None=None)->dict[str,Any]:
    return await (core or PlatformCoreClient()).record_statistical_coefficient(request.reasoning_ref,request.data)

async def add_interval(request:CoreIntervalRequest,core:PlatformCoreClient|None=None)->dict[str,Any]:
    return await (core or PlatformCoreClient()).record_statistical_interval(request.reasoning_ref,request.data)

async def add_interpretation(request:CoreInterpretationRequest,core:PlatformCoreClient|None=None)->dict[str,Any]:
    data=request.model_dump(mode="json",exclude={"reasoning_ref"},exclude_none=True); data["human_authored"]=True
    return await (core or PlatformCoreClient()).record_statistical_interpretation(request.reasoning_ref,data)
