"""Solace Enterprise Core — FastAPI application entry."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import require_master_key, settings
from app.core.database import init_engine
from app.core.exceptions import SolaceHTTPException, SecurityException, sanitize_error_detail
from app.core.logging_config import configure_logging
from app.services import bootstrap_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
  require_master_key()
  configure_logging()
  url = bootstrap_store.get_db_connection_url()
  if url:
    init_engine(url)
    logger.info("Database engine initialized")
    try:
      from app.core.database import session_scope
      from app.services import platform_settings_service

      with session_scope() as db:
        from app.services import permission_seed_service

        permission_seed_service.ensure_rbac_for_all_orgs(db)
        platform_settings_service.get_or_create_security_settings(db)
        platform_settings_service.apply_security_settings_to_runtime(db)
    except Exception:
      logger.warning("Could not load security settings from database")
  else:
    logger.info("Awaiting first-run database configuration")
  yield


app = FastAPI(
  title=settings.app_name,
  version=settings.app_version,
  lifespan=lifespan,
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.exception_handler(SolaceHTTPException)
async def solace_http_handler(request: Request, exc: SolaceHTTPException):
  return JSONResponse(status_code=exc.status_code, content=sanitize_error_detail(exc))


@app.exception_handler(SecurityException)
async def security_handler(request: Request, exc: SecurityException):
  return JSONResponse(status_code=403, content=sanitize_error_detail(exc))


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
  logger.exception("Unhandled error", exc_info=exc)
  return JSONResponse(status_code=500, content=sanitize_error_detail(exc))


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict:
  return {
    "status": "ok",
    "app": settings.app_name,
    "version": settings.app_version,
    "setup_complete": bootstrap_store.is_setup_complete(),
    "database_configured": bootstrap_store.get_db_connection_url() is not None,
  }
