"""API FastAPI para MathLite: ejecuta código y persiste casos de prueba."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from mathlite.pipeline import run_source  # noqa: E402
from api.storage import storage           # noqa: E402

app = FastAPI(title="MathLite API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).parent.parent / "web"


class RunRequest(BaseModel):
    source: str = Field(..., description="Código MathLite a ejecutar")
    execute: bool = True


class CaseCreate(BaseModel):
    title: str
    source: str
    result_summary: dict[str, Any] | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "storage": storage.backend}


@app.post("/api/run")
def run_endpoint(req: RunRequest) -> dict:
    result = run_source(req.source, execute=req.execute)
    return result.to_dict()


@app.get("/api/cases")
def list_cases() -> list[dict]:
    return storage.list()


@app.post("/api/cases", status_code=201)
def create_case(case: CaseCreate) -> dict:
    return storage.create(case.title, case.source, case.result_summary)


@app.delete("/api/cases/{case_id}")
def delete_case(case_id: str) -> dict:
    ok = storage.delete(case_id)
    if not ok:
        raise HTTPException(404, "caso no encontrado")
    return {"deleted": case_id}


# Servir el frontend estático
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")
