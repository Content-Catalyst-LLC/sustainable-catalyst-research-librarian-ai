from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from ..config import settings
from ..contracts.platform_core import CORE_MINIMUM_VERSION, CORE_SUPPORTED_MAJOR


class PlatformCoreError(RuntimeError):
    """Raised when Platform Core cannot satisfy a typed integration request."""

    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class CoreCompatibility:
    compatible: bool
    version: str
    minimum_version: str
    supported_major: int
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "version": self.version,
            "minimum_version": self.minimum_version,
            "supported_major": self.supported_major,
            "reason": self.reason,
        }


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = (value or "0.0.0").strip().split(".")
    numbers: list[int] = []
    for part in parts[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        numbers.append(int(digits or 0))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)  # type: ignore[return-value]


def compatibility(version: str) -> CoreCompatibility:
    current = _version_tuple(version)
    minimum = _version_tuple(settings.core_minimum_version or CORE_MINIMUM_VERSION)
    supported_major = int(settings.core_supported_major or CORE_SUPPORTED_MAJOR)
    if not version:
        return CoreCompatibility(False, "", settings.core_minimum_version, supported_major, "Core health response did not include a version.")
    if current[0] != supported_major:
        return CoreCompatibility(False, version, settings.core_minimum_version, supported_major, f"Core major version {current[0]} is outside the supported major {supported_major} contract.")
    if current < minimum:
        return CoreCompatibility(False, version, settings.core_minimum_version, supported_major, f"Core {version} is older than required {settings.core_minimum_version}.")
    return CoreCompatibility(True, version, settings.core_minimum_version, supported_major, "Compatible Platform Core contract.")


class PlatformCoreClient:
    """Typed async client for the private Platform Core service.

    The client deliberately targets Core's private `/v1` surface. Reads are
    non-destructive. Writes require the Core write key and are retried only for
    transport/transient HTTP failures; application 4xx responses are never
    silently retried.
    """

    transient_statuses = {408, 425, 429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        base_url: str | None = None,
        write_api_key: str | None = None,
        timeout_seconds: float | None = None,
        retry_limit: int | None = None,
        retry_backoff_seconds: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else settings.core_base_url).rstrip("/")
        self.write_api_key = write_api_key if write_api_key is not None else settings.core_write_api_key
        self.timeout_seconds = float(timeout_seconds if timeout_seconds is not None else settings.core_timeout_seconds)
        self.retry_limit = int(retry_limit if retry_limit is not None else settings.core_retry_limit)
        self.retry_backoff_seconds = float(retry_backoff_seconds if retry_backoff_seconds is not None else settings.core_retry_backoff_seconds)
        self.transport = transport

    def _configured(self) -> None:
        if not settings.core_enabled:
            raise PlatformCoreError("Platform Core integration is disabled by SC_RL_CORE_ENABLED.")
        if not self.base_url:
            raise PlatformCoreError("SC_RL_CORE_BASE_URL is required when Platform Core integration is enabled.")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        self._configured()
        headers = {
            "Accept": "application/json",
            "User-Agent": "SustainableCatalystResearchLibrarian/8.11.0",
            "X-SC-Research-Librarian-Version": "8.11.0",
        }
        if write:
            if not self.write_api_key:
                raise PlatformCoreError("SC_RL_CORE_WRITE_API_KEY is required for Platform Core writes.")
            headers["X-SC-API-Key"] = self.write_api_key
        attempts = max(1, self.retry_limit + 1)
        last_error: Exception | None = None
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout, transport=self.transport) as client:
            for attempt in range(attempts):
                try:
                    response = await client.request(method, path, json=payload, params=params, headers=headers)
                    if response.status_code in self.transient_statuses and attempt + 1 < attempts:
                        await asyncio.sleep(self.retry_backoff_seconds * (2 ** attempt))
                        continue
                    if response.status_code >= 400:
                        try:
                            detail: Any = response.json()
                        except ValueError:
                            detail = response.text[:1000]
                        raise PlatformCoreError(
                            f"Platform Core {method.upper()} {path} returned HTTP {response.status_code}.",
                            status_code=response.status_code,
                            detail=detail,
                        )
                    try:
                        body = response.json()
                    except ValueError as exc:
                        raise PlatformCoreError(f"Platform Core {method.upper()} {path} returned invalid JSON.") from exc
                    return body if isinstance(body, dict) else {"data": body}
                except PlatformCoreError:
                    raise
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        break
                    await asyncio.sleep(self.retry_backoff_seconds * (2 ** attempt))
        raise PlatformCoreError(f"Platform Core request failed after {attempts} attempt(s): {last_error}")

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def capability_readiness(self) -> dict[str, Any]:
        endpoints = {
            "research_objects": "/v1/research-objects/readiness",
            "unified_research_projects": "/v1/research/projects/readiness",
            "research_lineage": "/v1/research/lineage/readiness",
            "research_arguments": "/v1/research/arguments/readiness",
            "research_conclusions": "/v1/research/conclusions/readiness",
            "reproducible_research": "/v1/research/reproducibility/readiness",
            "statistical_reasoning": "/v1/analytics/statistical-reasoning/readiness",
            "unified_visual_reasoning": "/v1/visual-runtime/unified/readiness",
            "cross_product_exchange": "/v1/exchange/readiness",
            "project_state": "/v1/research/project-state/readiness",
            "finding_claim_evidence_intelligence": "/v1/research/intelligence/readiness",
        }

        async def one(name: str, path: str) -> tuple[str, dict[str, Any]]:
            try:
                body = await self._request("GET", path)
                return name, {"ok": True, "path": path, "data": body}
            except PlatformCoreError as exc:
                return name, {"ok": False, "path": path, "error": str(exc), "status_code": exc.status_code, "detail": exc.detail}

        pairs = await asyncio.gather(*(one(name, path) for name, path in endpoints.items()))
        return dict(pairs)

    async def create_source_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/source-snapshots", payload=payload, write=True)

    async def source_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/source-snapshots/{snapshot_id}")

    async def verify_source_snapshot(self, snapshot_id: str, content: str) -> dict[str, Any]:
        return await self._request("POST", f"/v1/source-snapshots/{snapshot_id}/verify", payload={"content": content})

    async def create_evidence_record(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/evidence-records", payload=payload, write=True)

    async def evidence_record(self, evidence_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/evidence-records/{evidence_id}")

    async def create_research_object(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/research-objects", payload=payload, write=True)

    async def research_object(self, entity_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/research-objects/{entity_id}")

    async def research_project_bundle(self, project_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/research/projects/{project_id}/bundle")

    async def create_unified_research_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/research/projects", payload={"data": payload}, write=True)

    async def create_exchange_package(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/exchange/packages", payload=payload, write=True)

    async def exchange_package(self, package_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/exchange/packages/{package_id}")

    async def research_intelligence_readiness(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/research/intelligence/readiness")

    async def create_research_finding(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/intelligence/projects/{project_id}/findings", payload={"data": payload}, write=True)

    async def create_research_claim(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/intelligence/projects/{project_id}/claims", payload={"data": payload}, write=True)

    async def create_research_evidence_link(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/intelligence/projects/{project_id}/evidence-links", payload={"data": payload}, write=True)

    async def research_intelligence_bundle(self, project_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/research/intelligence/projects/{project_id}/bundle")

    async def research_contradiction_candidates(self, project_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/research/intelligence/projects/{project_id}/contradiction-candidates")

    async def create_lineage_graph(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/lineage/projects/{project_id}/graphs", payload={"data": payload}, write=True)

    async def argument_readiness(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/research/arguments/readiness")

    async def create_argument(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/projects/{project_id}", payload={"data": payload}, write=True)

    async def add_argument_node(self, argument_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/{argument_id}/nodes", payload={"data": payload}, write=True)

    async def add_argument_edge(self, argument_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/{argument_id}/edges", payload={"data": payload}, write=True)

    async def create_argument_synthesis(self, argument_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/{argument_id}/syntheses", payload={"data": payload}, write=True)

    async def add_argument_synthesis_component(self, synthesis_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/syntheses/{synthesis_id}/components", payload={"data": payload}, write=True)

    async def add_argument_counterargument(self, argument_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/{argument_id}/counterarguments", payload={"data": payload}, write=True)

    async def add_argument_tension(self, argument_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/arguments/{argument_id}/tensions", payload={"data": payload}, write=True)

    async def argument_bundle(self, argument_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/research/arguments/{argument_id}/bundle")

    async def create_conclusion(self, argument_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/conclusions/arguments/{argument_id}", payload={"data": payload}, write=True)

    async def statistical_reasoning_readiness(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/analytics/statistical-reasoning/readiness")

    async def ingest_statistical_validation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/analytics/statistical-reasoning/ingest-validation", payload={"data": payload}, write=True)

    async def statistical_reasoning_bundle(self, reasoning_ref: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/analytics/statistical-reasoning/{reasoning_ref}/bundle")

    async def record_statistical_coefficient(self, reasoning_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/analytics/statistical-reasoning/{reasoning_ref}/coefficients", payload={"data": payload}, write=True)

    async def record_statistical_interval(self, reasoning_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/analytics/statistical-reasoning/{reasoning_ref}/intervals", payload={"data": payload}, write=True)

    async def record_statistical_interpretation(self, reasoning_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/analytics/statistical-reasoning/{reasoning_ref}/interpretations", payload={"data": payload}, write=True)

    async def create_statistical_reasoning_snapshot(self, reasoning_ref: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", f"/v1/analytics/statistical-reasoning/{reasoning_ref}/snapshots", payload={"data": payload or {}}, write=True)

    async def unified_visual_workspace_bundle(self, workspace_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/visual-runtime/unified/workspaces/{workspace_id}/bundle")

    async def project_state_readiness(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/research/project-state/readiness")

    async def create_project_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v1/research/project-state/states", payload={"data": payload}, write=True)

    async def create_project_state_version(self, state_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/project-state/states/{state_id}/versions", payload={"data": payload}, write=True)

    async def add_project_state_binding(self, state_id: str, version: int, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/project-state/states/{state_id}/versions/{version}/bindings", payload={"data": payload}, write=True)

    async def add_project_state_dependency(self, state_id: str, version: int, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/project-state/states/{state_id}/versions/{version}/dependencies", payload={"data": payload}, write=True)

    async def freeze_project_state_version(self, state_id: str, version: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/project-state/states/{state_id}/versions/{version}/freeze", payload={"data": payload or {}}, write=True)

    async def project_state_bundle(self, state_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/research/project-state/states/{state_id}/bundle")

    async def snapshot_project_state(self, state_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", f"/v1/research/project-state/states/{state_id}/snapshots", payload={"data": payload or {}}, write=True)
