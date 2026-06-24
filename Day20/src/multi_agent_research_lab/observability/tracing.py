"""Tracing hooks: structured logs + optional LangSmith export."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_tracing_configured = False


@dataclass(frozen=True)
class TracingInfo:
    enabled: bool
    project: str | None
    dashboard_url: str | None
    tavily_enabled: bool


def configure_tracing(settings: Settings | None = None) -> TracingInfo:
    """Enable LangSmith when LANGSMITH_API_KEY is set (also sets LANGCHAIN_* env vars)."""

    global _tracing_configured
    cfg = settings or get_settings()
    tavily_enabled = bool(cfg.tavily_api_key and cfg.tavily_api_key.strip())

    if not cfg.langsmith_api_key or not cfg.langsmith_api_key.strip():
        return TracingInfo(
            enabled=False,
            project=None,
            dashboard_url=None,
            tavily_enabled=tavily_enabled,
        )

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = cfg.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = cfg.langsmith_project
    _tracing_configured = True

    dashboard = f"https://smith.langchain.com/o/-/projects/p?name={cfg.langsmith_project}"
    logger.info("LangSmith tracing enabled for project=%s", cfg.langsmith_project)
    return TracingInfo(
        enabled=True,
        project=cfg.langsmith_project,
        dashboard_url=dashboard,
        tavily_enabled=tavily_enabled,
    )


def is_langsmith_enabled() -> bool:
    return _tracing_configured or os.environ.get("LANGCHAIN_TRACING_V2") == "true"


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Log span duration; nest in LangSmith when tracing is enabled."""

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    logger.info("span.start name=%s attrs=%s", name, attributes or {})

    if is_langsmith_enabled():
        try:
            from langsmith.run_helpers import trace

            with trace(name=name, run_type="chain", metadata=attributes or {}):
                try:
                    yield span
                finally:
                    span["duration_seconds"] = perf_counter() - started
            logger.info(
                "span.end name=%s duration=%.3fs attrs=%s",
                name,
                span["duration_seconds"],
                span["attributes"],
            )
            return
        except Exception as exc:
            logger.warning("LangSmith trace failed, using local span only: %s", exc)

    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
        logger.info(
            "span.end name=%s duration=%.3fs attrs=%s",
            name,
            span["duration_seconds"],
            span["attributes"],
        )
