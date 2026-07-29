"""Ponto de entrada da aplicação FastAPI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
import app.schemas  # resolve forward refs dos schemas

Path(settings.UPLOAD_DIR, "avatars").mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="API do CRM GD Conecta — MVP",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health", tags=["Infra"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}
