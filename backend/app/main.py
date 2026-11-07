"""SAMPURNA – 360° Human Wellness & Life Balance Platform: API entry point."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .database import engine
from .routers import assessments, auth, interviews, portal, privacy, wellness

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="SAMPURNA API",
    version="1.0.0",
    description=(
        "360° Human Wellness & Life Balance — *Balance Within. Harmony Around. Well-being for All.*\n\n"
        "REST API shared by the web PWA and future native mobile apps. Wellness scores are "
        "self-assessment indicators, not medical diagnoses or professional financial assessments."
    ),
    openapi_tags=[
        {"name": "Authentication"}, {"name": "Profile & Privacy"}, {"name": "Assessments & Agents"},
        {"name": "Interviews"}, {"name": "Wellness"}, {"name": "Coach & Counsellor Portal"}, {"name": "Administration"},
    ],
)
app.add_middleware(
    CORSMiddleware, allow_origins=get_settings().cors_origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = resp.headers.get("Cache-Control", "no-store")
    return resp


@app.exception_handler(LookupError)
async def lookup_handler(_: Request, exc: LookupError):
    return JSONResponse({"detail": str(exc)}, status_code=404)


for r in (auth.router, privacy.router, assessments.router, interviews.router, wellness.router, portal.router, portal.admin):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["Administration"])
def health():
    with engine.connect() as c:
        c.execute(text("select 1"))
    return {"status": "ok", "service": "sampurna-api"}
