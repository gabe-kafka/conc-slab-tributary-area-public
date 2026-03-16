from __future__ import annotations

import uuid
from pathlib import Path

import ezdxf
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
async def download_artifact(job_id: str, artifact_name: str):
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    artifact_path = job.artifacts.get(artifact_name)
    if not artifact_path or not Path(artifact_path).exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(path=artifact_path, filename=artifact_name)
