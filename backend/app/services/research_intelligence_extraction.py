from __future__ import annotations

import hashlib
import re
from typing import Any

from ..clients.platform_core import PlatformCoreClient
from ..config import settings
from ..contracts.research_intelligence_extraction import (
    CORE_RESEARCH_INTELLIGENCE_CONTRACT,
    RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
    CoreResearchCandidatePromotionRequest,
    EvidencePassageInput,
    ResearchIntelligenceCandidate,
    ResearchIntelligenceExtractionRequest,
)
from ..store import store

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[\(])")
_WS_RE = re.compile(r"\s+")

_FINDING_CUES = {
    "observed": "observation",
    "measured": "observation",
    "we found": "result",
    "results show": "result",
    "results showed": "result",
    "was higher": "result",
    "was lower": "result",
    "were higher": "result",
    "were lower": "result",
    "increased": "result",
    "decreased": "result",
    "estimate": "estimate",
    "estimated": "estimate",
    "pattern": "pattern",
    "anomaly": "anomaly",
    "no significant": "negative_result",
    "did not": "negative_result",
    "limitation": "limitation",
}
_CLAIM_CUES = {
    "suggests": "interpretive",
    "suggested": "interpretive",
    "indicates": "interpretive",
    "indicated": "interpretive",
    "consistent with": "interpretive",
    "associated with": "descriptive",
    "correlated with": "descriptive",
    "compared with": "comparative",
    "compared to": "comparative",
    "more than": "comparative",
    "less than": "comparative",
    "predict": "predictive",
    "forecast": "predictive",
    "may": "interpretive",
    "might": "interpretive",
    "could": "interpretive",
    "causes": "causal",
    "caused": "causal",
    "leads to": "causal",
    "resulted in": "causal",
}
_UNCERTAINTY_CUES = (
    "may", "might", "could", "possibly", "potentially", "uncertain", "uncertainty",
    "confidence interval", "credible interval", "approximately", "suggests", "appears",
)


def capabilities() -> dict[str, Any]:
    return {
        "schema": RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_RESEARCH_INTELLIGENCE_CONTRACT,
        "deterministic_sentence_extraction": True,
        "candidate_findings": True,
        "candidate_claims": True,
        "uncertainty_cue_detection": True,
        "passage_level_provenance": True,
        "human_review_required_for_core_promotion": True,
        "default_review_decision": "pending",
        "default_evidence_relation": "contextualizes",
        "automatic_truth_determination": False,
        "automatic_claim_acceptance": False,
        "automatic_finding_acceptance": False,
        "automatic_evidence_strength_judgment": False,
        "semantic_contradiction_resolution": False,
        "core_is_governed_registry": True,
    }


def _clean(value: str) -> str:
    return _WS_RE.sub(" ", str(value or "")).strip()


def _sentences(text: str) -> list[str]:
    cleaned = _clean(text)
    if not cleaned:
        return []
    parts = _SENTENCE_RE.split(cleaned)
    return [p.strip(" \t\r\n-•") for p in parts if p.strip(" \t\r\n-•")]


def _uncertainty(text: str) -> list[str]:
    low = text.lower()
    return sorted({cue for cue in _UNCERTAINTY_CUES if cue in low})


def _classification(sentence: str) -> tuple[str | None, str | None, list[str]]:
    low = sentence.lower()
    finding_hits = [(cue, kind) for cue, kind in _FINDING_CUES.items() if cue in low]
    claim_hits = [(cue, kind) for cue, kind in _CLAIM_CUES.items() if cue in low]
    if finding_hits:
        cue, kind = finding_hits[0]
        return "finding", kind, [f"finding-cue:{cue}"]
    if claim_hits:
        cue, kind = claim_hits[0]
        return "claim", kind, [f"claim-cue:{cue}"]
    # Declarative scholarly sentences remain candidate claims, never accepted claims.
    if len(sentence.split()) >= 10 and not sentence.endswith("?"):
        return "claim", "descriptive", ["declarative-sentence"]
    return None, None, []


def _resolve_core_evidence(passage: EvidencePassageInput) -> tuple[str, str]:
    if passage.core_evidence_id:
        return passage.core_evidence_id, "explicit-core-evidence-id"
    binding = store.platform_core_binding("evidence-record", passage.local_evidence_id)
    if binding and binding.get("sync_state") == "synced" and binding.get("core_id"):
        return str(binding["core_id"]), "v8.7-evidence-binding"
    return "", "unbound-local-evidence"


def _candidate_id(project_id: str, passage: EvidencePassageInput, sentence: str, candidate_type: str) -> str:
    raw = "\n".join((project_id, passage.local_evidence_id, candidate_type, sentence))
    return f"rl-candidate-{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


def extract_candidates(request: ResearchIntelligenceExtractionRequest) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for passage in request.passages:
        core_evidence_id, evidence_resolution = _resolve_core_evidence(passage)
        for sentence in _sentences(passage.text):
            if len(sentence.split()) < request.minimum_sentence_words:
                skipped.append({"local_evidence_id": passage.local_evidence_id, "reason": "below-minimum-word-count", "text": sentence})
                continue
            ctype, subtype, basis = _classification(sentence)
            if ctype is None:
                skipped.append({"local_evidence_id": passage.local_evidence_id, "reason": "no-deterministic-candidate-rule", "text": sentence})
                continue
            if ctype == "finding" and not request.include_findings:
                continue
            if ctype == "claim" and not request.include_claims:
                continue
            fingerprint = hashlib.sha256(sentence.lower().encode()).hexdigest()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            cid = _candidate_id(request.core_project_id, passage, sentence, ctype)
            evidence_relation = passage.relation_hint or "contextualizes"
            evidence = [{
                "local_evidence_id": passage.local_evidence_id,
                "core_evidence_id": core_evidence_id,
                "core_evidence_resolution": evidence_resolution,
                "relation": evidence_relation,
                "relation_supplied_explicitly": passage.relation_hint is not None,
                "canonical_source_id": passage.canonical_source_id or "",
                "source_title": passage.source_title or "",
                "passage_id": passage.passage_id or "",
                "chunk_id": passage.chunk_id or "",
                "section_path": passage.section_path,
                "page_start": passage.page_start,
                "page_end": passage.page_end,
            }]
            item = ResearchIntelligenceCandidate(
                candidate_id=cid,
                candidate_type=ctype,
                text=sentence,
                title=(sentence[:117] + "...") if len(sentence) > 120 else sentence,
                finding_type=subtype if ctype == "finding" else None,
                claim_type=subtype if ctype == "claim" else None,
                classification_basis=basis,
                uncertainty_cues=_uncertainty(sentence),
                evidence=evidence,
                review_decision="pending",
                provenance={
                    "source_product": "research-librarian",
                    "source_release": settings.release_version,
                    "extraction_schema": RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
                    "deterministic_extraction": True,
                    "generative_extraction": False,
                    "research_question": request.research_question,
                    "truth_determination_performed": False,
                    "evidence_strength_judgment_performed": False,
                },
            ).model_dump()
            candidates.append(item)
            if len(candidates) >= request.max_candidates:
                break
        if len(candidates) >= request.max_candidates:
            break
    return {
        "schema": RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_RESEARCH_INTELLIGENCE_CONTRACT,
        "core_project_id": request.core_project_id,
        "research_question": request.research_question,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "skipped": skipped[:200],
        "review_required": True,
        "promotion_ready_count": sum(
            1 for c in candidates if c.get("review_decision") == "approved" and c.get("reviewer_ref")
        ),
        "governance": capabilities(),
    }


def _core_evidence_refs(candidate: ResearchIntelligenceCandidate) -> list[tuple[str, dict[str, Any]]]:
    refs: list[tuple[str, dict[str, Any]]] = []
    for evidence in candidate.evidence:
        ref = str(evidence.get("core_evidence_id") or "").strip()
        if not ref:
            local_id = str(evidence.get("local_evidence_id") or "").strip()
            binding = store.platform_core_binding("evidence-record", local_id) if local_id else None
            if binding and binding.get("sync_state") == "synced" and binding.get("core_id"):
                ref = str(binding["core_id"])
        if not ref:
            raise ValueError("Every promoted candidate evidence item must resolve to a synced v8.7 Core evidence record.")
        refs.append((ref, evidence))
    if not refs:
        raise ValueError("A promoted candidate must contain at least one evidence item.")
    return refs


async def promote_candidate(
    request: CoreResearchCandidatePromotionRequest,
    client: PlatformCoreClient | None = None,
) -> dict[str, Any]:
    candidate = request.candidate
    refs = _core_evidence_refs(candidate)
    core = client or PlatformCoreClient()
    provenance = {
        **candidate.provenance,
        "source_product": "research-librarian",
        "source_release": settings.release_version,
        "extraction_schema": RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
        "candidate_id": candidate.candidate_id,
        "review_decision": candidate.review_decision,
        "reviewer_ref": candidate.reviewer_ref,
        "reviewer_note": candidate.reviewer_note or "",
        "automated_truth_judgment": False,
        "automated_acceptance": False,
    }
    if candidate.candidate_type == "finding":
        payload = {
            "finding_key": candidate.candidate_id,
            "title": candidate.title or candidate.text[:200],
            "statement": candidate.text,
            "finding_type": candidate.finding_type or "result",
            "status": "proposed",
            "source_refs": [ref for ref, _ in refs],
            "uncertainty": {"detected_cues": candidate.uncertainty_cues},
            "limitations": ["Candidate extracted by the Research Librarian; requires governed review before stronger status."],
            "metadata": {"research_librarian_candidate": True, "classification_basis": candidate.classification_basis},
            "provenance": provenance,
            "created_by": request.created_by,
        }
        created = await core.create_research_finding(request.core_project_id, payload)
        target_type = "finding"
    else:
        payload = {
            "claim_key": candidate.candidate_id,
            "claim_text": candidate.text,
            "claim_type": candidate.claim_type or "descriptive",
            "status": "proposed",
            "polarity": "not_applicable",
            "uncertainty": {"detected_cues": candidate.uncertainty_cues},
            "qualifications": ["Candidate extracted by the Research Librarian; proposition has not been accepted as true."],
            "metadata": {"research_librarian_candidate": True, "classification_basis": candidate.classification_basis},
            "provenance": provenance,
            "created_by": request.created_by,
        }
        created = await core.create_research_claim(request.core_project_id, payload)
        target_type = "claim"
    target_id = str(created.get("id") or "")
    if not target_id:
        raise RuntimeError("Platform Core research-intelligence response did not include an object id.")
    links: list[dict[str, Any]] = []
    for index, (ref, evidence) in enumerate(refs, start=1):
        relation = request.evidence_relation or str(evidence.get("relation") or "contextualizes")
        link_payload = {
            "evidence_link_key": f"{candidate.candidate_id}:evidence:{index}",
            "evidence_ref": ref,
            "evidence_kind": "evidence-record",
            "target_type": target_type,
            "target_id": target_id,
            "relation": relation,
            "locator": str(evidence.get("passage_id") or evidence.get("chunk_id") or "") or None,
            "declared_strength": request.declared_strength,
            "assessment_basis": request.assessment_basis or (
                "Evidence relationship supplied by reviewer/caller." if request.evidence_relation else "Contextual relationship preserved from Librarian candidate; no evidence-strength judgment performed."
            ),
            "assessment": {"reviewer_ref": candidate.reviewer_ref, "automatic_judgment": False},
            "uncertainty": {"candidate_uncertainty_cues": candidate.uncertainty_cues},
            "metadata": {"research_librarian_candidate_id": candidate.candidate_id},
            "provenance": provenance,
            "created_by": request.created_by,
        }
        link_payload = {k: v for k, v in link_payload.items() if v is not None}
        links.append(await core.create_research_evidence_link(request.core_project_id, link_payload))
    return {
        "schema": RESEARCH_INTELLIGENCE_EXTRACTION_SCHEMA,
        "release": settings.release_version,
        "core_contract": CORE_RESEARCH_INTELLIGENCE_CONTRACT,
        "candidate_id": candidate.candidate_id,
        "reviewed_by": candidate.reviewer_ref,
        "core_object_type": target_type,
        "core_object": created,
        "evidence_links": links,
        "governance": {
            "registered_as_proposed": True,
            "truth_determined": False,
            "evidence_strength_judged_automatically": False,
            "human_review_gate_satisfied": True,
        },
    }
