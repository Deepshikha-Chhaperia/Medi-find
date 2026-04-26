"""
MediFind — FastAPI Backend Entry Point
Zero-config SQLite with manual vector search | Groq LLaMA 3.3-70B | sentence-transformers
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure backend-local absolute imports resolve when uvicorn is launched from repo root.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Load .env first (before importing modules that read env vars)
load_dotenv()

from db.database import init_db
from api.search import router as search_router
from api.facilities import router as facilities_router
from api.ingest import router as ingest_router
from api.stats import router as stats_router
from api.public_data import router as public_router

app = FastAPI(
    title="MediFind API",
    description="Agentic healthcare intelligence — search 10,000+ facility reports in plain English.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server and Vercel
_origins = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(search_router)
app.include_router(facilities_router)
app.include_router(ingest_router)
app.include_router(stats_router)
app.include_router(public_router)


@app.on_event("startup")
def startup():
    """Initialise DB schema on startup (idempotent)."""
    try:
        init_db()
        print("[MediFind] Database ready ✓")
    except Exception as e:
        print(f"[MediFind] DB init warning: {e}")


@app.get("/")
def root():
    return {
        "service": "MediFind API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
