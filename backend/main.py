"""Servidor principal FastAPI (Fase 12 Core).

Conserva intactos los modelos de datos de SQLAlchemy, PostgreSQL (Neon) y bloqueos de concurrencia.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import router as api_router
from data.database import get_engine

app = FastAPI(
    title="USAER 2E · Backend Core (Fase 12)",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
