from __future__ import annotations

import hashlib
import json
from typing import Any

from ..clients.platform_core import PlatformCoreClient
from ..config import settings
from ..contracts.visual_research import (
    VISUAL_RESEARCH_SCHEMA,
    CORE_VISUAL_OBJECT_CONTRACT,
    CORE_SCENE_CONTRACT,
    CORE_UNIFIED_VISUAL_CONTRACT,
    CORE_CROSS_PRODUCT_VISUAL_CONTRACT,
    VisualResearchPlanRequest,
    VisualResearchPlan,
    CoreVisualResearchPromotionRequest,
)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def capabilities() -> dict[str, Any]:
    return {
        "schema": VISUAL_RESEARCH_SCHEMA,
        "release": settings.release_version,
        "core_visual_object_contract": CORE_VISUAL_OBJECT_CONTRACT,
        "core_scene_contract": CORE_SCENE_CONTRACT,
        "core_unified_visual_contract": CORE_UNIFIED_VISUAL_CONTRACT,
        "core_cross_product_visual_contract": CORE_CROSS_PRODUCT_VISUAL_CONTRACT,
        "visualization_kinds": [
            "citation-network", "evidence-map", "claim-map", "finding-map", "contradiction-map",
            "argument-graph", "statistical-result-view", "uncertainty-view", "provenance-graph",
            "research-timeline", "source-lineage", "concept-map", "generic",
        ],
        "renderer_neutral_specs": True,
        "explicit_relation_only": True,
        "source_hash_provenance": True,
        "linked_view_planning": True,
        "core_visual_object_registration": True,
        "core_session_visual_binding": True,
        "human_review_required_for_core_promotion": True,
        "librarian_renders_visuals": False,
        "core_layout_computation_required": False,
        "automatic_graph_edge_inference": False,
        "automatic_claim_or_finding_promotion": False,
        "automatic_visual_truth_promotion": False,
        "automatic_argument_ranking": False,
        "automatic_statistical_interpretation": False,
    }


def build_plan(request: VisualResearchPlanRequest) -> dict[str, Any]:
    raw = request.model_dump(mode="json", exclude_none=True)
    plan_id = "rl-visual-plan-" + _hash(raw)[:24]

    entities: list[dict[str, Any]] = []
    for sequence, item in enumerate(request.entities, 1):
        data = item.model_dump(mode="json", exclude_none=True)
        data["sequence"] = sequence
        data["entity_key"] = "rl-visual-entity-" + _hash({"plan": plan_id, "ref": item.local_ref})[:24]
        data["identity_inferred"] = False
        entities.append(data)

    relations: list[dict[str, Any]] = []
    for sequence, item in enumerate(request.relations, 1):
        data = item.model_dump(mode="json", exclude_none=True)
        data["sequence"] = sequence
        data["relation_key"] = "rl-visual-relation-" + _hash({"plan": plan_id, "ref": item.relation_ref})[:24]
        data["relation_supplied_explicitly"] = True
        relations.append(data)

    views = [v.model_dump(mode="json", exclude_none=True) for v in request.views]
    if not views:
        views = [{
            "view_ref": "primary",
            "kind": request.visual_kind,
            "title": request.title,
            "entity_refs": [x.local_ref for x in request.entities],
            "relation_refs": [x.relation_ref for x in request.relations],
            "encodings": {},
            "filters": {},
            "linked_view_refs": [],
            "layout_hint": "renderer-selected",
            "annotations": [],
        }]

    for view in views:
        view["renderer_neutral"] = True
        view["layout_computed_by_librarian"] = False
        view["view_key"] = "rl-visual-view-" + _hash({"plan": plan_id, "ref": view["view_ref"]})[:24]

    plan = VisualResearchPlan(
        plan_id=plan_id,
        core_project_id=request.core_project_id,
        core_session_id=request.core_session_id,
        title=request.title,
        research_question=request.research_question,
        visual_kind=request.visual_kind,
        entities=entities,
        relations=relations,
        views=views,
        source_content_hashes=dict(request.source_content_hashes),
        limitations=list(request.limitations),
        renderer_policy={
            "renderer_neutral": True,
            "renderer_selected_by_librarian": False,
            "layout_computed_by_librarian": False,
            "scene_execution_by_librarian": False,
            "core_semantic_visual_authority": True,
            "specialist_renderer_authority_retained": True,
        },
        provenance={
            "librarian_release": settings.release_version,
            "visual_relations_inferred": False,
            "visual_layout_inferred": False,
            "claims_promoted_by_visualization": False,
            "findings_promoted_by_visualization": False,
            "statistical_interpretation_generated": False,
            "truth_determined": False,
        },
    )
    return {
        "schema": VISUAL_RESEARCH_SCHEMA,
        "release": settings.release_version,
        "plan": plan.model_dump(mode="json", exclude_none=True),
        "governance": capabilities(),
    }


async def readiness(core: PlatformCoreClient | None = None) -> dict[str, Any]:
    client = core or PlatformCoreClient()
    object_model = await client.visual_reasoning_readiness()
    unified = await client.unified_visual_reasoning_readiness()
    return {
        "schema": VISUAL_RESEARCH_SCHEMA,
        "release": settings.release_version,
        "visual_reasoning": object_model,
        "unified_visual_reasoning": unified,
        "renderer_neutral": bool(object_model.get("renderer_neutral", True)),
        "automatic_truth_promotion": bool(object_model.get("automatic_truth_promotion", False)),
        "core_visual_authority": True,
    }


def _extract_id(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    nested = payload.get("data")
    if isinstance(nested, dict):
        return _extract_id(nested, *keys)
    return ""


async def promote_plan(request: CoreVisualResearchPromotionRequest, core: PlatformCoreClient | None = None) -> dict[str, Any]:
    client = core or PlatformCoreClient()
    plan = request.plan

    visual_payload = {
        "visual_key": plan.plan_id,
        "project_ref": plan.core_project_id,
        "title": plan.title,
        "visual_kind": plan.visual_kind,
        "status": "draft",
        "renderer_neutral": True,
        "visibility": request.visibility,
        "metadata": {
            "source": "research-librarian",
            "librarian_release": settings.release_version,
            "reviewer_ref": plan.reviewer_ref,
            "research_question": plan.research_question,
            "source_content_hashes": plan.source_content_hashes,
            "limitations": plan.limitations,
            "visual_relations_inferred": False,
            "automatic_truth_promotion": False,
        },
    }
    visual = await client.create_visual_reasoning_object(visual_payload)
    visual_id = _extract_id(visual, "visual_entity_id", "id", "visual_id")
    if not visual_id:
        raise RuntimeError("Platform Core did not return a canonical visual object ID.")

    layers: list[dict[str, Any]] = []
    for sequence, view in enumerate(plan.views, 1):
        layer = await client.add_visual_reasoning_layer(visual_id, {
            "layer_key": view.get("view_key") or view.get("view_ref"),
            "title": view.get("title") or view.get("view_ref"),
            "layer_kind": view.get("kind") or plan.visual_kind,
            "sequence": sequence,
            "visible": True,
            "metadata": {"renderer_neutral": True, "layout_hint": view.get("layout_hint")},
        })
        layers.append(layer)

    elements: list[dict[str, Any]] = []
    local_to_core_element: dict[str, str] = {}
    for item in plan.entities:
        element = await client.add_visual_reasoning_element(visual_id, {
            "element_key": item["entity_key"],
            "element_kind": item["entity_type"],
            "label": item["label"],
            "source_ref": item.get("core_object_id") or item["local_ref"],
            "role": item.get("role", "context"),
            "metadata": {
                "local_ref": item["local_ref"],
                "evidence_refs": item.get("evidence_refs", []),
                **dict(item.get("metadata") or {}),
            },
        })
        elements.append(element)
        local_to_core_element[item["local_ref"]] = _extract_id(element, "element_id", "id") or item["entity_key"]

    relations: list[dict[str, Any]] = []
    for item in plan.relations:
        relation = await client.add_visual_reasoning_relation(visual_id, {
            "relation_key": item["relation_key"],
            "source_element_id": local_to_core_element[item["source_local_ref"]],
            "target_element_id": local_to_core_element[item["target_local_ref"]],
            "relation": item["relation"],
            "metadata": {
                "rationale": item.get("rationale"),
                "evidence_refs": item.get("evidence_refs", []),
                "relation_supplied_explicitly": True,
                **dict(item.get("metadata") or {}),
            },
        })
        relations.append(relation)

    snapshot = None
    if request.create_snapshot:
        snapshot = await client.create_visual_reasoning_snapshot(visual_id, {
            "snapshot_key": "rl-visual-snapshot-" + _hash({"plan": plan.plan_id, "reviewer": plan.reviewer_ref})[:24],
            "metadata": {"plan_id": plan.plan_id, "reviewer_ref": plan.reviewer_ref, "immutable_requested": True},
        })

    binding = None
    if request.bind_to_core_session and plan.core_session_id:
        binding = await client.bind_unified_visual({
            "session_id": plan.core_session_id,
            "project_id": plan.core_project_id,
            "product_key": "research-librarian",
            "visual_ref": visual_id,
            "visual_kind": plan.visual_kind,
            "source_refs": [x.get("core_object_id") or x["local_ref"] for x in plan.entities],
            "metadata": {"plan_id": plan.plan_id, "reviewer_ref": plan.reviewer_ref, "renderer_neutral": True},
        })

    return {
        "schema": VISUAL_RESEARCH_SCHEMA,
        "release": settings.release_version,
        "plan_id": plan.plan_id,
        "visual": visual,
        "layers": layers,
        "elements": elements,
        "relations": relations,
        "snapshot": snapshot,
        "session_binding": binding,
        "governance": {
            "human_reviewed": True,
            "reviewer_ref": plan.reviewer_ref,
            "relations_inferred": False,
            "layout_executed_by_librarian": False,
            "visual_rendered_by_librarian": False,
            "truth_determined": False,
        },
    }
