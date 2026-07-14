from __future__ import annotations
from typing import Any
from .config import settings
from .models import RetrievedSource
from .provider import generate_answer as provider_generate_answer

GENERATION_ADAPTER_SCHEMA = "sc-generation-adapter/1.0"


def adapter_status() -> dict[str, Any]:
    return {
        "schema": GENERATION_ADAPTER_SCHEMA,
        "provider": settings.provider,
        "model": settings.gemini_model if settings.provider == "gemini" else "",
        "replaceable": True,
        "retrieval_provider_independent": True,
        "deterministic_fallback": True,
        "fallback": "deterministic",
    }


async def generate(
    question: str,
    matches: list[RetrievedSource],
    related: list[RetrievedSource],
    history: list[dict[str, Any]],
    route_hint: dict[str, Any],
    calibration: dict[str, Any],
) -> str:
    """Provider-independent synthesis boundary.

    Durable retrieval, evidence, projects, governance, and exports never depend on
    this adapter. A provider may be replaced without changing the project model.
    """
    return await provider_generate_answer(question, matches, related, history, route_hint, calibration)
