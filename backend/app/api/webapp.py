from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from ..services.independent_web_app import (
    WEB_APP_ROOT,
    web_app_manifest,
    web_app_capabilities,
)

router = APIRouter(tags=["Independent Research Librarian Web App"])

def _file(name: str, media_type: str) -> FileResponse:
    path = (WEB_APP_ROOT / name).resolve()
    root = WEB_APP_ROOT.resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=404, detail="Web app asset not found.")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Web app asset not found.")
    return FileResponse(path, media_type=media_type)

@router.get("/research-librarian", include_in_schema=False)
def web_app_entry_no_slash() -> FileResponse:
    return _file("index.html", "text/html; charset=utf-8")

@router.get("/research-librarian/", include_in_schema=False)
def web_app_entry() -> FileResponse:
    return _file("index.html", "text/html; charset=utf-8")

@router.get("/research-librarian/app-manifest.json", include_in_schema=False)
def web_app_manifest_endpoint() -> JSONResponse:
    return JSONResponse(web_app_manifest())

@router.get("/research-librarian/capabilities.json", include_in_schema=False)
def web_app_capabilities_endpoint() -> JSONResponse:
    return JSONResponse(web_app_capabilities())

@router.get("/research-librarian/assets/app.css", include_in_schema=False)
def web_app_css() -> FileResponse:
    return _file("app.css", "text/css; charset=utf-8")

@router.get("/research-librarian/assets/app.js", include_in_schema=False)
def web_app_js() -> FileResponse:
    return _file("app.js", "application/javascript; charset=utf-8")
