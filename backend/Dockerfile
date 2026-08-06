# ─────────────────────────────────────────────────────────────────────────────
# Sententia.ai Backend — Dockerfile
#
# Works on both Render.com (uses $PORT env var) and HF Spaces (port 7860)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE ${PORT:-10000}

# ── Start server — uses $PORT if set (Render), else 10000 ─────────────────────
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1
