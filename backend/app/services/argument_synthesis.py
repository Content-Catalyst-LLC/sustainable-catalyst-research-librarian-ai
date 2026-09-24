from __future__ import annotations

import hashlib
import json
from typing import Any

from ..clients.platform_core import PlatformCoreClient
from ..config import settings
from ..contracts.argument_synthesis import (
    ARGUMENT_SYNTHESIS_SCHEMA,
    CORE_ARGUMENT_CONTRACT,
    ArgumentSynthesisPlan,
    ArgumentSynthesisPlanRequest,
    CoreArgumentSynthesisPromotionRequest,
)


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def capabilities() -> dict[str, Any]:
    return {
        "schema": ARGUMENT_SYNTHESIS_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_ARGUMENT_CONTRACT,
        "declared_argument_planning": True,
        "core_contradiction_candidate_inspection": True,
        "governed_argument_graph_promotion": True,
        "open_tension_registration": True,
        "researcher_authored_synthesis_promotion": True,
        "human_review_required_for_core_promotion": True,
        "default_review_decision": "pending",
        "automatic_argument_generation": False,
        "automatic_relation_inference": False,
        "automatic_contradiction_resolution": False,
        "automatic_argument_ranking": False,
        "automatic_best_argument_selection": False,
        "automatic_synthesis_generation": False,
        "automatic_conclusion_generation": False,
        "automatic_truth_determination": False,
    }


def build_plan(request: ArgumentSynthesisPlanRequest) -> dict[str, Any]:
    canonical = request.model_dump(mode="json", exclude_none=True)
    plan_id = "rl-argument-plan-" + _hash(canonical)[:24]
    node_keys: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    for index, node in enumerate(request.nodes, start=1):
        key = "rl-node-" + _hash({"plan": plan_id, "ref": node.local_ref})[:24]
        node_keys[node.local_ref] = key
        nodes.append({
            "local_ref": node.local_ref,
            "node_key": key,
            "node_type": node.core_object_type,
            "role": node.role,
            "source_ref": node.core_object_id,
            "statement_text": node.statement_text,
            "citation_refs": list(node.citation_refs),
            "uncertainty": dict(node.uncertainty),
            "metadata": {**dict(node.metadata), "librarian_sequence": index},
        })
    relations: list[dict[str, Any]] = []
    for relation in request.relations:
        relations.append({
            "edge_key": "rl-edge-" + _hash({"plan": plan_id, **relation.model_dump(mode="json")})[:24],
            "source_local_ref": relation.source_local_ref,
            "target_local_ref": relation.target_local_ref,
            "source_node_key": node_keys[relation.source_local_ref],
            "target_node_key": node_keys[relation.target_local_ref],
            "relation": relation.relation,
            "rationale": relation.rationale,
            "evidence_refs": list(relation.evidence_refs),
            "metadata": dict(relation.metadata),
            "relation_supplied_explicitly": True,
        })
    tensions = []
    for tension in request.tensions:
        item = tension.model_dump(mode="json", exclude_none=True)
        item["tension_key"] = item.get("tension_key") or "rl-tension-" + _hash({"plan": plan_id, **item})[:24]
        item["researcher_declared"] = True
        tensions.append(item)
    synthesis = None
    if request.synthesis:
        synthesis = request.synthesis.model_dump(mode="json")
        synthesis["synthesis_key"] = "rl-synthesis-" + _hash({"plan": plan_id, **synthesis})[:24]
        synthesis["status"] = "draft"
        synthesis["researcher_authored"] = True
    argument = {
        "argument_key": "rl-argument-" + _hash({"plan": plan_id, "title": request.title})[:24],
        "title": request.title,
        "thesis_text": request.thesis_text,
        "central_claim_ref": request.central_claim_ref,
        "argument_type": request.argument_type,
        "status": "draft",
        "scope": {"source": "research-librarian-v8.10", "plan_id": plan_id},
        "limitations": list(request.limitations),
        "metadata": dict(request.metadata),
    }
    plan = ArgumentSynthesisPlan(
        plan_id=plan_id,
        core_project_id=request.core_project_id,
        argument={k: v for k, v in argument.items() if v is not None},
        nodes=[{k: v for k, v in x.items() if v is not None} for x in nodes],
        relations=[{k: v for k, v in x.items() if v is not None} for x in relations],
        tensions=tensions,
        synthesis=synthesis,
        provenance={
            "librarian_release": settings.release_version,
            "core_contract": CORE_ARGUMENT_CONTRACT,
            "argument_generated_by_model": False,
            "relations_inferred_by_model": False,
            "truth_determined": False,
        },
    )
    return {
        "schema": ARGUMENT_SYNTHESIS_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_ARGUMENT_CONTRACT,
        "plan": plan.model_dump(mode="json", exclude_none=True),
        "governance": capabilities(),
    }


async def contradiction_candidates(core_project_id: str, core: PlatformCoreClient | None = None) -> dict[str, Any]:
    client = core or PlatformCoreClient()
    result = await client.research_contradiction_candidates(core_project_id)
    return {
        "schema": ARGUMENT_SYNTHESIS_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_ARGUMENT_CONTRACT,
        "core_project_id": core_project_id,
        "core": result,
        "review_required_before_tension_registration": True,
        "automatic_contradiction_resolution": False,
        "automatic_truth_determination": False,
    }


async def promote_plan(request: CoreArgumentSynthesisPromotionRequest, core: PlatformCoreClient | None = None) -> dict[str, Any]:
    client = core or PlatformCoreClient()
    plan = request.plan
    argument_payload = {
        **dict(plan.argument),
        "provenance": {
            **dict(plan.provenance),
            "librarian_plan_id": plan.plan_id,
            "reviewer_ref": plan.reviewer_ref,
            "human_review_required": True,
            "automated_truth_judgment": False,
        },
        "created_by": request.created_by,
    }
    argument = await client.create_argument(plan.core_project_id, argument_payload)
    argument_id = str(argument.get("id") or argument.get("argument_id") or "")
    if not argument_id:
        raise ValueError("Platform Core argument creation did not return an argument id.")

    node_ids: dict[str, str] = {}
    created_nodes = []
    for node in plan.nodes:
        payload = {k: v for k, v in dict(node).items() if k not in {"local_ref"} and v is not None}
        payload["provenance"] = {
            "librarian_plan_id": plan.plan_id,
            "reviewer_ref": plan.reviewer_ref,
            "relation_inference_performed": False,
        }
        payload["created_by"] = request.created_by
        created = await client.add_argument_node(argument_id, payload)
        local_ref = str(node.get("local_ref") or "")
        core_node_id = str(created.get("id") or "")
        if local_ref and core_node_id:
            node_ids[local_ref] = core_node_id
        created_nodes.append(created)

    created_edges = []
    for relation in plan.relations:
        source = node_ids.get(str(relation.get("source_local_ref") or ""))
        target = node_ids.get(str(relation.get("target_local_ref") or ""))
        if not source or not target:
            raise ValueError("A declared relation could not resolve its promoted Core argument nodes.")
        payload = {
            "edge_key": relation["edge_key"],
            "source_node_id": source,
            "target_node_id": target,
            "relation": relation["relation"],
            "rationale": relation.get("rationale"),
            "evidence_refs": relation.get("evidence_refs", []),
            "metadata": {**dict(relation.get("metadata") or {}), "relation_supplied_explicitly": True},
            "provenance": {"librarian_plan_id": plan.plan_id, "reviewer_ref": plan.reviewer_ref, "relation_inferred": False},
            "created_by": request.created_by,
        }
        created_edges.append(await client.add_argument_edge(argument_id, {k: v for k, v in payload.items() if v is not None}))

    created_tensions = []
    for tension in plan.tensions:
        payload = dict(tension)
        payload.pop("researcher_declared", None)
        payload["provenance"] = {"librarian_plan_id": plan.plan_id, "reviewer_ref": plan.reviewer_ref, "resolved_by_librarian": False}
        payload["created_by"] = request.created_by
        created_tensions.append(await client.add_argument_tension(argument_id, payload))

    synthesis = None
    synthesis_components = []
    if plan.synthesis:
        s = dict(plan.synthesis)
        component_refs = list(s.pop("component_local_refs", []))
        s.pop("researcher_authored", None)
        s["provenance"] = {"librarian_plan_id": plan.plan_id, "reviewer_ref": plan.reviewer_ref, "generated_by_librarian": False}
        s["created_by"] = request.created_by
        synthesis = await client.create_argument_synthesis(argument_id, s)
        synthesis_id = str(synthesis.get("id") or "")
        for local_ref in component_refs:
            source_node_id = node_ids.get(local_ref)
            if not source_node_id:
                continue
            component = await client.add_argument_synthesis_component(synthesis_id, {
                "component_key": "rl-component-" + _hash({"synthesis": synthesis_id, "ref": local_ref})[:24],
                "source_type": "argument-node",
                "source_ref": source_node_id,
                "role": "context",
                "researcher_note": "Included by reviewer-approved Librarian synthesis plan.",
                "provenance": {"librarian_plan_id": plan.plan_id, "reviewer_ref": plan.reviewer_ref},
                "created_by": request.created_by,
            })
            synthesis_components.append(component)

    return {
        "schema": ARGUMENT_SYNTHESIS_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_ARGUMENT_CONTRACT,
        "plan_id": plan.plan_id,
        "reviewed_by": plan.reviewer_ref,
        "argument": argument,
        "nodes": created_nodes,
        "edges": created_edges,
        "tensions": created_tensions,
        "synthesis": synthesis,
        "synthesis_components": synthesis_components,
        "governance": {
            "argument_ranked": False,
            "contradictions_resolved": False,
            "synthesis_generated_automatically": False,
            "conclusion_generated": False,
            "truth_determined": False,
        },
    }
