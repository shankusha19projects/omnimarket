"""OmniMarket Intelligence Terminal — FastAPI application entry point.

Run:  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import db
from backend.api.routes import router
from backend.config import ROOT, app_name, env
from backend.services import user_state
from backend.utils.http import ProviderError, close_client
from backend.utils.logging_setup import get_logger, setup_logging

setup_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    version = db.migrate()
    user_state.seed_defaults()
    log.info(f"{app_name()} starting (schema v{version})")
    yield
    await close_client()


app = FastAPI(
    title=f"{app_name()} API",
    version="1.0.0",
    description="Local financial intelligence terminal. All market data carries provenance (provider, source URL, retrieval time, cache status).",
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in (env("CORS_ORIGINS") or "").split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.exception_handler(ProviderError)
async def provider_error_handler(_: Request, exc: ProviderError) -> JSONResponse:
    return JSONResponse(status_code=503 if not exc.rate_limited else 429,
                        content={"error": exc.message, "provider": exc.provider, "detail": f"Data provider '{exc.provider}' unavailable: {exc.message}"})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": f"{type(exc).__name__}: {exc}"})


app.include_router(router)

# Serve the production frontend build (npm run build) from the same origin when present.
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        target = DIST / path
        if path and target.is_file() and Path(target).resolve().is_relative_to(DIST.resolve()):
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
