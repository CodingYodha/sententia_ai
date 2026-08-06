"""
Sententia.ai — FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import health, intake, rag, structures, compliance, diagram, review

settings = get_settings()

# ── Parse CORS origins ────────────────────────────────────────────────────────
_raw_origins = []
_regex_origins = []

for o in settings.cors_origins.split(","):
    o = o.strip()
    if not o:
        continue
    if "*" in o:
        # Convert simple wildcard to regex
        _regex = o.replace(".", r"\.").replace("*", ".*")
        _regex_origins.append(_regex)
    else:
        _raw_origins.append(o)

origin_regex_str = None
if _regex_origins:
    origin_regex_str = "^(" + "|".join(_regex_origins) + ")$"

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
    allow_origin_regex=origin_regex_str,
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
