"""
Production AI Agent — Day 12 final lab.

Combines 12-factor config, API key auth, Redis-backed rate limiting,
monthly cost guard, conversation history, health/readiness probes,
and graceful shutdown.
"""
import json
import logging
import os
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, get_usage, record_usage
from app.rate_limiter import check_rate_limit
from app.redis_client import init_redis, redis_available
from app.session import append_message, get_history
from app.llm import ask as llm_ask, get_llm_provider

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_is_ready = False
_in_flight_requests = 0
_request_count = 0
_error_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready, _in_flight_requests
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
    }))
    init_redis()
    _is_ready = True
    logger.info(json.dumps({
        "event": "ready",
        "redis": redis_available(),
        "use_mock_llm": settings.use_mock_llm,
        "openai_configured": settings.openai_configured,
        "llm_provider": get_llm_provider(),
    }))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown_start", "in_flight": _in_flight_requests}))
    timeout = 30
    elapsed = 0
    while _in_flight_requests > 0 and elapsed < timeout:
        time.sleep(1)
        elapsed += 1
    logger.info(json.dumps({"event": "shutdown_complete"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count, _in_flight_requests
    start = time.time()
    _request_count += 1
    _in_flight_requests += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
            "instance_id": INSTANCE_ID,
        }))
        return response
    except Exception:
        _error_count += 1
        raise
    finally:
        _in_flight_requests -= 1


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128, description="User identifier")
    question: str = Field(..., min_length=1, max_length=2000, description="Question for the agent")


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    turn: int
    served_by: str
    storage: str
    timestamp: str


@app.get("/", include_in_schema=False)
def ui():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "UI not found. Use /api for service info."}


@app.get("/api", tags=["Info"])
def api_info():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
        "llm": get_llm_provider(),
        "openai_configured": settings.openai_configured,
        "ui": "/",
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "usage": "GET /usage/{user_id}",
            "history": "GET /history/{user_id}",
        },
    }


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    check_rate_limit(body.user_id)
    check_budget(body.user_id)

    history = get_history(body.user_id)
    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
        "history_len": len(history),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    try:
        answer, input_tokens, output_tokens, model_label = llm_ask(body.question, history=history)
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc

    append_message(body.user_id, "user", body.question)
    append_message(body.user_id, "assistant", answer)
    record_usage(body.user_id, input_tokens, output_tokens)

    updated_history = get_history(body.user_id)
    user_turns = sum(1 for m in updated_history if m["role"] == "user")

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=model_label,
        turn=user_turns,
        served_by=INSTANCE_ID,
        storage="redis" if redis_available() else "in-memory",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/auth/verify", tags=["Agent"])
def verify_key(_key: str = Depends(verify_api_key)):
    """Quick check that X-API-Key is valid (use from demo UI)."""
    return {"ok": True, "message": "API key is valid"}


@app.get("/usage/{user_id}", tags=["Agent"])
def usage(user_id: str, _key: str = Depends(verify_api_key)):
    return get_usage(user_id)


@app.get("/history/{user_id}", tags=["Agent"])
def history(user_id: str, _key: str = Depends(verify_api_key)):
    messages = get_history(user_id)
    return {"user_id": user_id, "messages": messages, "count": len(messages)}


@app.get("/health", tags=["Operations"])
def health():
    redis_ok = redis_available() if settings.redis_url else None
    status = "ok"
    if settings.redis_url and redis_ok is False:
        status = "degraded"
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {
            "llm": get_llm_provider(),
            "use_mock_llm": settings.use_mock_llm,
            "openai_configured": settings.openai_configured,
            "redis": redis_ok if settings.redis_url else "not_configured",
            "redis_url_set": bool(settings.redis_url),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready")
    if settings.redis_url and not redis_available():
        raise HTTPException(status_code=503, detail="Redis not available")
    return {
        "ready": True,
        "instance_id": INSTANCE_ID,
        "in_flight_requests": _in_flight_requests,
    }


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "instance_id": INSTANCE_ID,
        "storage": "redis" if redis_available() else "in-memory",
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum, "instance_id": INSTANCE_ID}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info("Starting %s on %s:%s", settings.app_name, settings.host, settings.port)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
