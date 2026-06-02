"""FastAPI server for TravelBuddy web demo."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
WEB_DIR = Path(__file__).resolve().parent / "web"
EXAMPLES_PATH = Path(__file__).resolve().parent / "examples.json"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(ROOT_DIR / ".env")

from agent.graph import run_agent  # noqa: E402

app = FastAPI(title="TravelBuddy Demo", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    provider: str | None = None
    today: str = "2026-05-31"


class ChatResponse(BaseModel):
    query: str
    final_answer: str
    tool_calls: list[dict]
    provider: str
    model_name: str | None = None


@app.get("/api/health")
def health() -> dict:
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_google = bool(os.getenv("GOOGLE_API_KEY"))
    return {
        "status": "ok",
        "default_provider": os.getenv("TRAVEL_AGENT_PROVIDER", "openai"),
        "credentials": {"openai": has_openai, "google": has_google},
    }


@app.get("/api/examples")
def list_examples() -> list[dict]:
    return json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")
    try:
        result = run_agent(
            query,
            provider=body.provider,
            today=body.today,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatResponse(
        query=result.query,
        final_answer=result.final_answer,
        tool_calls=[t.model_dump() for t in result.tool_calls],
        provider=result.provider,
        model_name=result.model_name,
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")
