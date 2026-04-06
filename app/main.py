from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import ezdxf
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.runtime_paths import bundle_root, user_data_root
from app.services.inspection import display_layer_name, save_upload
from app.services.jobs import JobManager

ROOT_DIR = bundle_root()
APP_DIR = ROOT_DIR / "app"
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
VAR_DIR = user_data_root() / "var"
ENGINE_DIR = APP_DIR / "engine" / "legacy"
DEMO_DIR = ROOT_DIR / "demo"
DEMO_INPUT_PATH = DEMO_DIR / "INPUT.dxf"

app = FastAPI(title="Two-Way Slab Tributary Area")

_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra_origin = os.environ.get("CORS_ORIGIN")
if _extra_origin:
    _allowed_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["display_layer_name"] = display_layer_name
manager = JobManager(base_dir=VAR_DIR, engine_dir=ENGINE_DIR)


@app.on_event("startup")
def startup_event() -> None:
    manager.start()


def _session_id(request: Request) -> str:
    return request.cookies.get("session_id") or uuid.uuid4().hex


def _apply_session_cookie(request: Request, response) -> None:
    response.set_cookie("session_id", _session_id(request), httponly=True, samesite="lax")


def _inspect_payload(request: Request, session_id: str, filename: str, payload: bytes, status_code: int = 200):
    try:
        draft = save_upload(payload, filename, session_id, manager.drafts_dir)
    except ezdxf.DXFStructureError:
        response = templates.TemplateResponse(
            "index.html",
            {"request": request, "page": "index", "error": "DXF could not be parsed."},
            status_code=400,
        )
        _apply_session_cookie(request, response)
        return response

    manager.register_draft(draft)
    response = templates.TemplateResponse(
        "review.html",
        {"request": request, "page": "review", "draft": draft},
        status_code=status_code,
    )
    _apply_session_cookie(request, response)
    return response


@app.get("/")
async def index(request: Request):
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page": "index",
        },
    )
    _apply_session_cookie(request, response)
    return response


@app.post("/inspect")
async def inspect(request: Request, upload: UploadFile = File(...)):
    session_id = _session_id(request)
    if not upload.filename or not upload.filename.lower().endswith(".dxf"):
        response = templates.TemplateResponse(
            "index.html",
            {"request": request, "page": "index", "error": "Upload a `.dxf` file."},
            status_code=400,
        )
        _apply_session_cookie(request, response)
        return response

    payload = await upload.read()
    return _inspect_payload(request, session_id, upload.filename, payload)


@app.post("/inspect/demo")
async def inspect_demo(request: Request):
    if not DEMO_INPUT_PATH.exists():
        response = templates.TemplateResponse(
            "index.html",
            {"request": request, "page": "index", "error": "Demo DXF is not available."},
            status_code=500,
        )
        _apply_session_cookie(request, response)
        return response

    return _inspect_payload(
        request=request,
        session_id=_session_id(request),
        filename="DEMO_INPUT.dxf",
        payload=DEMO_INPUT_PATH.read_bytes(),
    )


@app.post("/jobs")
async def create_job(
    request: Request,
    draft_id: str = Form(...),
    source_units: str = Form("in"),
):
    draft = manager.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    form = await request.form()
    layer_mapping = {
        "boundary": form.getlist("boundary_layers"),
        "wall": form.getlist("wall_layers"),
        "support_point": form.getlist("support_point_layers"),
        "column_label": form.getlist("column_label_layers"),
        "floor_label": form.getlist("floor_label_layers"),
    }

    if not layer_mapping["boundary"] or not layer_mapping["support_point"]:
        response = templates.TemplateResponse(
            "review.html",
            {
                "request": request,
                "page": "review",
                "draft": draft,
                "error": "Select at least one boundary layer and one column layer.",
            },
            status_code=400,
        )
        _apply_session_cookie(request, response)
        return response

    job = manager.create_job(
        session_id=_session_id(request),
        draft_id=draft_id,
        source_units=source_units,
        layer_mapping=layer_mapping,
    )
    response = RedirectResponse(url=f"/jobs/{job.id}", status_code=303)
    _apply_session_cookie(request, response)
    return response


@app.get("/jobs/{job_id}")
async def job_detail(request: Request, job_id: str):
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    response = templates.TemplateResponse(
        "job.html",
        {"request": request, "page": "job", "job": job},
    )
    _apply_session_cookie(request, response)
    return response


@app.get("/api/jobs/{job_id}")
async def job_detail_api(job_id: str):
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_dict()


@app.get("/jobs/{job_id}/artifacts/{artifact_name}")
@app.get("/api/jobs/{job_id}/artifacts/{artifact_name}")
async def download_artifact(job_id: str, artifact_name: str):
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    artifact_path = job.artifacts.get(artifact_name)
    if not artifact_path or not Path(artifact_path).exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(path=artifact_path, filename=artifact_name)


# --- JSON API endpoints for Next.js frontend ---


@app.post("/api/upload")
async def api_upload(upload: UploadFile = File(...)):
    if not upload.filename or not upload.filename.lower().endswith(".dxf"):
        raise HTTPException(status_code=400, detail="Upload a .dxf file.")

    session_id = uuid.uuid4().hex
    payload = await upload.read()
    try:
        draft = save_upload(payload, upload.filename, session_id, manager.drafts_dir)
    except ezdxf.DXFStructureError:
        raise HTTPException(status_code=400, detail="DXF could not be parsed.")

    manager.register_draft(draft)
    return draft.to_dict()


@app.post("/api/upload/demo")
async def api_upload_demo():
    if not DEMO_INPUT_PATH.exists():
        raise HTTPException(status_code=500, detail="Demo DXF is not available.")

    session_id = uuid.uuid4().hex
    payload = DEMO_INPUT_PATH.read_bytes()
    draft = save_upload(payload, "DEMO_INPUT.dxf", session_id, manager.drafts_dir)
    manager.register_draft(draft)
    return draft.to_dict()


class CreateJobRequest(BaseModel):
    draft_id: str
    source_units: str = "in"
    layer_mapping: Dict[str, List[str]]


@app.post("/api/jobs")
async def api_create_job(body: CreateJobRequest):
    draft = manager.get_draft(body.draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    if not body.layer_mapping.get("boundary") or not body.layer_mapping.get("support_point"):
        raise HTTPException(
            status_code=400,
            detail="Select at least one boundary layer and one column layer.",
        )

    session_id = uuid.uuid4().hex
    job = manager.create_job(
        session_id=session_id,
        draft_id=body.draft_id,
        source_units=body.source_units,
        layer_mapping=body.layer_mapping,
    )
    return {"job_id": job.id, "status": job.status}


@app.get("/api/jobs/{job_id}/geometry")
async def api_job_geometry(job_id: str):
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    geometry_path = job.artifacts.get("geometry.json")
    if not geometry_path or not Path(geometry_path).exists():
        raise HTTPException(status_code=404, detail="Geometry data not available.")

    data = json.loads(Path(geometry_path).read_text(encoding="utf-8"))
    return JSONResponse(content=data)
