from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from live_llm import build_baseline_messages, usage_from_response
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


def _extract_name(text: str) -> str | None:
    match = re.search(r"tên (?:là|mình là)\s+([^.,!\?]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


class BaselineAgent:
    """Agent A: within-session memory only, no persistent User.md."""

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}
        self.llm = None if force_offline else self._maybe_build_langchain_agent()
        self.langchain_agent = self.llm

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if self.llm is not None:
            return self._reply_live(user_id, thread_id, message)
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        session = self.sessions.get(thread_id)
        return session.token_usage if session else 0

    def prompt_token_usage(self, thread_id: str) -> int:
        session = self.sessions.get(thread_id)
        return session.prompt_tokens_processed if session else 0

    def compaction_count(self, thread_id: str) -> int:
        return 0

    def _session(self, thread_id: str) -> SessionState:
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
        return self.sessions[thread_id]

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        session = self._session(thread_id)
        context_text = "\n".join(item["content"] for item in session.messages)
        prompt_tokens = estimate_tokens(context_text) + estimate_tokens(message)
        session.prompt_tokens_processed += prompt_tokens

        session.messages.append({"role": "user", "content": message})
        answer = self._offline_response(session.messages, message)
        session.messages.append({"role": "assistant", "content": answer})

        answer_tokens = estimate_tokens(answer)
        session.token_usage += answer_tokens

        return {
            "answer": answer,
            "agent_tokens": answer_tokens,
            "prompt_tokens": prompt_tokens,
            "mode": "offline",
        }

    def _offline_response(self, messages: list[dict[str, str]], message: str) -> str:
        lower = message.lower()
        if message.strip().endswith("?"):
            if "tên" in lower:
                for item in reversed(messages):
                    if name := _extract_name(item["content"]):
                        return f"Trong phiên này mình ghi nhận tên bạn là {name}."
                return "Trong phiên này mình chưa thấy bạn nói tên."
            if "style" in lower or "trả lời" in lower:
                for item in reversed(messages):
                    if "ngắn gọn" in item["content"].lower():
                        return "Bạn thích trả lời ngắn gọn, có bullet và ví dụ thực tế."
                return "Trong phiên này mình chưa ghi nhận style trả lời cụ thể."
            return "Mình chỉ nhớ thông tin trong cùng thread hiện tại."

        return "Đã ghi nhận trong phiên này."

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        session = self._session(thread_id)
        session.messages.append({"role": "user", "content": message})

        response = self.llm.invoke(build_baseline_messages(session.messages))
        answer = str(response.content)
        usage = usage_from_response(response)

        session.messages.append({"role": "assistant", "content": answer})
        session.prompt_tokens_processed += usage.prompt_tokens or estimate_tokens(message)
        session.token_usage += usage.completion_tokens or estimate_tokens(answer)

        return {
            "answer": answer,
            "agent_tokens": usage.completion_tokens,
            "prompt_tokens": usage.prompt_tokens,
            "mode": "live",
            "model": self.config.model.model_name,
        }

    def _maybe_build_langchain_agent(self):
        try:
            if not self.config.model.api_key and self.config.model.provider not in {"ollama"}:
                return None
            return build_chat_model(self.config.model)
        except Exception:
            return None
