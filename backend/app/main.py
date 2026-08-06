"""
Sententia.ai — FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import health, intake, rag, structures, compliance, diagram, review

settings = get_settings()

# ── Parse CORS origins ────────────────────────────────────────────────────────
_raw_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Sententia.ai API — AI-powered cross-border fund structuring. "
        "Proposes investment structures and validates compliance for "
        "multi-jurisdiction FDI scenarios."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=_raw_origins,
    allow_origin_regex=r"https://.*\.pages\.dev",  # Cloudflare Pages wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(intake.router)
app.include_router(rag.router)
app.include_router(structures.router)
app.include_router(compliance.router)
app.include_router(diagram.router)
app.include_router(review.router)


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
