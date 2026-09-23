from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from .. import __version__
from ..contracts.sources import CitationRegisterRequest, SourceResolveRequest
from ..source_identity import CITATION_GRAPH_SCHEMA, SOURCE_IDENTITY_SCHEMA, SourceIdentityConflict, get_source_graph_store

router = APIRouter(prefix="/v1/sources", tags=["source-identity"])
_registered = False

def register_authenticated_routes(require_key: Any) -> None:
    global _registered
    if _registered: return
    _registered = True

    @router.get("/capabilities", dependencies=[Depends(require_key)])
    def capabilities() -> dict[str,Any]:
        runtime=get_source_graph_store().runtime()
        return {"ok":True,"version":__version__,**runtime,"identifier_priority":["doi","arxiv","pmid","isbn","url"],"deduplication":"stable-identifiers-then-bibliographic-fingerprint","citation_stubs":True,"platform_core_governs_promoted_evidence":True}

    @router.post("/resolve", dependencies=[Depends(require_key)])
    def resolve(payload: SourceResolveRequest) -> dict[str,Any]:
        try:
            result=get_source_graph_store().resolve(payload.model_dump(),register_citations=payload.register_citations)
        except SourceIdentityConflict as exc:
            raise HTTPException(status_code=409,detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc
        return {"ok":True,"version":__version__,"result":result}

    @router.get("/{source_id}", dependencies=[Depends(require_key)])
    def get_source(source_id:str)->dict[str,Any]:
        item=get_source_graph_store().get(source_id)
        if not item: raise HTTPException(status_code=404,detail="Canonical source not found.")
        return {"ok":True,"version":__version__,"source":item}

    @router.get("/{source_id}/graph", dependencies=[Depends(require_key)])
    def graph(source_id:str,limit:int=200)->dict[str,Any]:
        item=get_source_graph_store().graph(source_id,limit)
        if not item: raise HTTPException(status_code=404,detail="Canonical source not found.")
        return {"ok":True,"version":__version__,"graph":item}

    @router.post("/{source_id}/citations", dependencies=[Depends(require_key)])
    def citations(source_id:str,payload:CitationRegisterRequest)->dict[str,Any]:
        if not get_source_graph_store().get(source_id): raise HTTPException(status_code=404,detail="Canonical source not found.")
        result=get_source_graph_store().register_references(source_id,payload.references)
        return {"ok":True,"version":__version__,"schema":CITATION_GRAPH_SCHEMA,"canonical_source_id":source_id,"result":result}
