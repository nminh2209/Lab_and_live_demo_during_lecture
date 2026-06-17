"""
Assignment 11 — Production pipeline plugins: rate limiting, audit log, monitoring.
"""
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from google.adk.plugins import base_plugin
from google.genai import types


class RateLimitPlugin(base_plugin.BasePlugin):
    """Sliding-window rate limiter — blocks abusive users before the LLM is called."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(name="rate_limiter")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_windows: dict[str, deque] = defaultdict(deque)
        self.blocked_count = 0
        self.total_count = 0

    def _check_rate(self, user_id: str) -> tuple[bool, float]:
        """Return (allowed, wait_seconds_if_blocked)."""
        now = time.time()
        window = self.user_windows[user_id]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            wait = self.window_seconds - (now - window[0])
            return False, max(wait, 0.0)
        window.append(now)
        return True, 0.0

    async def on_user_message_callback(self, *, invocation_context, user_message):
        self.total_count += 1
        user_id = "anonymous"
        if invocation_context and getattr(invocation_context, "user_id", None):
            user_id = invocation_context.user_id
        allowed, wait = self._check_rate(user_id)
        if not allowed:
            self.blocked_count += 1
            return types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text=f"Rate limit exceeded. Please wait {wait:.0f} seconds."
                )],
            )
        return None


class AuditLogPlugin(base_plugin.BasePlugin):
    """Records every interaction for compliance — never blocks, only logs."""

    def __init__(self):
        super().__init__(name="audit_log")
        self.logs: list[dict] = []
        self._pending: dict[str, dict] = {}

    def _session_key(self, callback_context) -> str:
        session_id = getattr(callback_context, "session_id", None) or "default"
        return str(session_id)

    async def on_user_message_callback(self, *, invocation_context, user_message):
        key = str(id(invocation_context)) if invocation_context else "default"
        text = ""
        if user_message and user_message.parts:
            for part in user_message.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
        self._pending[key] = {
            "timestamp": datetime.utcnow().isoformat(),
            "input": text,
            "start_time": time.time(),
            "blocked_by": None,
        }
        return None

    async def after_model_callback(self, *, callback_context, llm_response):
        key = self._session_key(callback_context)
        entry = self._pending.pop(key, {
            "timestamp": datetime.utcnow().isoformat(),
            "input": "",
            "start_time": time.time(),
        })
        output = ""
        if hasattr(llm_response, "content") and llm_response.content:
            for part in llm_response.content.parts:
                if hasattr(part, "text") and part.text:
                    output += part.text
        entry["output"] = output
        entry["latency_ms"] = round((time.time() - entry.get("start_time", time.time())) * 1000, 2)
        self.logs.append(entry)
        return llm_response

    def export_json(self, filepath: str = "audit_log.json") -> str:
        path = Path(filepath)
        path.write_text(json.dumps(self.logs, indent=2, default=str), encoding="utf-8")
        return str(path.resolve())


@dataclass
class MonitoringAlert:
    """Tracks block rates and fires alerts when thresholds are exceeded."""

    block_rate_threshold: float = 0.5
    rate_limit_threshold: int = 5
    judge_fail_threshold: int = 3
    alerts: list[str] = field(default_factory=list)

    def check_metrics(self, plugins: list) -> dict:
        """Inspect plugins and return metrics + alerts."""
        self.alerts = []
        metrics = {
            "input_blocks": 0,
            "output_blocks": 0,
            "rate_limit_blocks": 0,
            "output_redactions": 0,
            "audit_entries": 0,
        }
        for plugin in plugins:
            name = getattr(plugin, "name", type(plugin).__name__)
            if name == "input_guardrail":
                metrics["input_blocks"] = getattr(plugin, "blocked_count", 0)
            elif name == "output_guardrail":
                metrics["output_blocks"] = getattr(plugin, "blocked_count", 0)
                metrics["output_redactions"] = getattr(plugin, "redacted_count", 0)
            elif name == "rate_limiter":
                metrics["rate_limit_blocks"] = getattr(plugin, "blocked_count", 0)
            elif name == "audit_log":
                metrics["audit_entries"] = len(getattr(plugin, "logs", []))

        total_blocks = (
            metrics["input_blocks"]
            + metrics["output_blocks"]
            + metrics["rate_limit_blocks"]
        )
        if total_blocks >= self.rate_limit_threshold:
            self.alerts.append(
                f"High block volume: {total_blocks} total blocks detected."
            )
        if metrics["output_blocks"] >= self.judge_fail_threshold:
            self.alerts.append(
                f"LLM judge fail rate elevated: {metrics['output_blocks']} outputs blocked."
            )
        return {"metrics": metrics, "alerts": self.alerts}
