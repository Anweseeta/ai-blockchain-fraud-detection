"""Fraud-risk API. All ML artifacts load once at startup; requests never train."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database.mongo import get_collection
from .explainability.shap_explainer import ShapExplainerService
from .ml.loader import load_artifacts
from .routes import explain as explain_routes
from .routes import history as history_routes
from .routes import predict as predict_routes
from .routes import system as system_routes
from .services.inference import InferenceService
from .services.persistence import InMemoryPredictionStore, MongoPredictionStore
from .services.risk import RiskService

log = logging.getLogger("fraud_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. validated ML artifacts (fail fast: the API is useless without them)
    artifacts = load_artifacts(
        settings.PREPROCESSOR_PATH,
        settings.XGBOOST_PATH,
        settings.MODEL_METADATA_PATH,
        settings.RISK_CONFIG_PATH,
        settings.MODEL_VERSION,
    )
    if settings.THRESHOLD_OVERRIDE:
        artifacts.threshold = float(settings.THRESHOLD_OVERRIDE)
        log.warning("threshold overridden via env: %s", artifacts.threshold)

    app.state.artifacts = artifacts
    app.state.inference = InferenceService(artifacts)
    app.state.risk = RiskService(artifacts.risk_config)
    app.state.shap = ShapExplainerService(
        artifacts.xgb_model, artifacts.feature_names_out
    )

    # 2. persistence (graceful: API stays up even if MongoDB is down)
    collection, db_status = await get_collection(
        settings.MONGO_URI, settings.MONGO_DB, settings.MONGO_COLLECTION
    )
    app.state.db_status = db_status
    app.state.store = (
        MongoPredictionStore(collection) if collection is not None
        else InMemoryPredictionStore()
    )
    if db_status != "connected":
        log.warning("prediction history persistence: %s (in-memory fallback)", db_status)

    log.info("artifacts loaded; threshold=%s", artifacts.threshold)
    yield


app = FastAPI(
    title="Blockchain Fraud Risk API",
    description=(
        "Scores Ethereum accounts for fraud risk using the validated XGBoost model. "
        "Explanations are SHAP model contributions, not causal claims. "
        "Prediction is not proof of fraud."
    ),
    version=settings.MODEL_VERSION,
    lifespan=lifespan,
)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        max_age=600,
    )


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """Reject oversized payloads before parsing."""
    limit = settings.MAX_CSV_BYTES if request.url.path.endswith("/batch") else settings.MAX_JSON_BYTES
    clen = request.headers.get("content-length")
    if clen and clen.isdigit() and int(clen) > limit:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": f"request body exceeds {limit} bytes"},
        )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "request validation failed",
                 "errors": _sanitize(exc.errors())},
    )


def _sanitize(obj):
    """Make validation error payloads JSON-safe (inf/nan/exceptions are not)."""
    import json
    import math

    if isinstance(obj, float) and not math.isfinite(obj):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # never leak stack traces or internals to clients
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "internal server error"},
    )


app.include_router(predict_routes.router, prefix="/api/v1", tags=["predict"])
app.include_router(explain_routes.router, prefix="/api/v1", tags=["explain"])
app.include_router(system_routes.router, prefix="/api/v1", tags=["system"])
app.include_router(history_routes.router, prefix="/api/v1", tags=["history"])


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "blockchain-fraud-risk-api", "docs": "/docs"}
