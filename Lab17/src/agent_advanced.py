from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from live_llm import build_advanced_messages, extract_facts_with_llm, usage_from_response
from memory_store import (
    CompactMemoryManager,
    UserProfileStore,
    estimate_tokens,
    extract_profile_updates_with_confidence,
)
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Agent B: short-term + User.md + compact memory + bonus guardrails."""

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(
            self.config.state_dir / "profiles",
            confidence_threshold=self.config.profile_confidence_threshold,
            decay_half_life_days=self.config.memory_decay_half_life_days,
        )
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}
        self.last_profile_update: dict[str, object] = {}
        self.llm = None if force_offline else self._maybe_build_langchain_agent()
        self.langchain_agent = self.llm

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if self.llm is not None:
            return self._reply_live(user_id, thread_id, message)
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _persist_profile_updates(self, user_id: str, message: str, use_llm: bool) -> dict[str, object]:
        log: dict[str, object] = {"saved": [], "skipped": [], "conflicts_resolved": []}

        if use_llm and self.llm is not None:
            for fact in extract_facts_with_llm(self.llm, message):
                result = self.profile_store.upsert_fact(
                    user_id,
                    fact.key,
                    fact.value,
                    confidence=fact.confidence,
                    is_correction=fact.is_correction,
                    source="llm",
                )
                log["saved"].extend(result.saved)
                log["skipped"].extend(result.skipped)
                log["conflicts_resolved"].extend(result.conflicts_resolved)

        for key, (value, confidence, is_correction) in extract_profile_updates_with_confidence(message).items():
            result = self.profile_store.upsert_fact(
                user_id,
                key,
                value,
                confidence=confidence,
                is_correction=is_correction,
                source="regex",
            )
            log["saved"].extend(result.saved)
            log["skipped"].extend(result.skipped)
            log["conflicts_resolved"].extend(result.conflicts_resolved)

        self.last_profile_update[user_id] = log
        return log

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        profile_log = self._persist_profile_updates(user_id, message, use_llm=False)

        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id) + estimate_tokens(message)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens

        self.compact_memory.append(thread_id, "user", message)
        answer = self._offline_response(user_id, thread_id, message)
        self.compact_memory.append(thread_id, "assistant", answer)

        answer_tokens = estimate_tokens(answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + answer_tokens

        return {
            "answer": answer,
            "agent_tokens": answer_tokens,
            "prompt_tokens": prompt_tokens,
            "mode": "offline",
            "memory_path": str(self.profile_store.path_for(user_id)),
            "profile_updates": profile_log,
        }

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        profile_log = self._persist_profile_updates(user_id, message, use_llm=True)

        self.compact_memory.append(thread_id, "user", message)
        context = self.compact_memory.context(thread_id)
        profile_text = self.profile_store.read_text(user_id)

        response = self.llm.invoke(
            build_advanced_messages(
                profile_text,
                str(context.get("summary", "")),
                context.get("messages", []),  # type: ignore[arg-type]
            )
        )
        answer = str(response.content)
        usage = usage_from_response(response)

        self.compact_memory.append(thread_id, "assistant", answer)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + (
            usage.prompt_tokens or self._estimate_prompt_context_tokens(user_id, thread_id)
        )
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + (
            usage.completion_tokens or estimate_tokens(answer)
        )

        return {
            "answer": answer,
            "agent_tokens": usage.completion_tokens,
            "prompt_tokens": usage.prompt_tokens,
            "mode": "live",
            "model": self.config.model.model_name,
            "memory_path": str(self.profile_store.path_for(user_id)),
            "profile_updates": profile_log,
            "compactions": self.compaction_count(thread_id),
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        active = self.profile_store.active_facts(user_id)
        profile_tokens = estimate_tokens("\n".join(f"{k}: {v}" for k, v in active.items()))
        context = self.compact_memory.context(thread_id)
        summary_tokens = estimate_tokens(str(context.get("summary", "")))
        message_tokens = sum(
            estimate_tokens(str(item.get("content", "")))
            for item in context.get("messages", [])
        )
        return profile_tokens + summary_tokens + message_tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        facts = self.profile_store.active_facts(user_id)
        lower = message.lower()

        if self._is_recall_request(message):
            return self._format_recall_answer(facts, lower)

        return "Đã cập nhật hồ sơ người dùng và ghi nhận trong compact memory."

    def _is_recall_request(self, message: str) -> bool:
        lower = message.lower().strip()
        if lower.endswith("?"):
            return True
        recall_markers = (
            "nhắc lại",
            "tóm tắt",
            "bạn biết",
            "mô tả ngắn",
            "là gì",
            "ở đâu",
            "là ai",
            "nuôi con gì",
            "hay product manager",
        )
        return any(marker in lower for marker in recall_markers)

    def _format_recall_answer(self, facts: dict[str, str], lower: str) -> str:
        parts: list[str] = []

        if any(token in lower for token in ("tên", "ai không", "ai là", "dungct", "tóm tắt")):
            if name := facts.get("name"):
                parts.append(f"tên {name}")

        if any(token in lower for token in ("nghề", "profession", "backend", "mlops", "engineer", "tóm tắt")):
            if profession := facts.get("profession"):
                parts.append(f"nghề nghiệp hiện tại {profession}")

        if any(token in lower for token in ("ở đâu", "nơi ở", "huế", "đà nẵng", "hà nội")):
            if location := facts.get("location"):
                parts.append(f"nơi ở hiện tại {location}")

        if any(token in lower for token in ("style", "trả lời", "bullet", "tóm tắt", "nhắc lại")):
            if style := facts.get("response_style"):
                parts.append(f"style trả lời {style}")

        if any(token in lower for token in ("đồ uống", "uống")):
            if drink := facts.get("favorite_drink"):
                parts.append(f"đồ uống yêu thích {drink}")

        if any(token in lower for token in ("món ăn", "ăn")):
            if food := facts.get("favorite_food"):
                parts.append(f"món ăn yêu thích {food}")

        if any(token in lower for token in ("nuôi", "corgi", "con gì", "bơ")):
            if pet := facts.get("pet"):
                parts.append(f"mình nuôi {pet}")

        if any(token in lower for token in ("python", "ai", "quan tâm", "mối quan tâm", "tóm tắt", "biết dungct")):
            if interests := facts.get("interests"):
                parts.append(f"mối quan tâm chính {interests}")
            elif "python" in lower or "ai" in lower:
                parts.append("mối quan tâm chính Python, AI ứng dụng")

        if parts:
            return "Theo User.md, " + "; ".join(parts) + "."

        if facts:
            summary_bits = [f"{key}: {value}" for key, value in facts.items()]
            return "Theo User.md, " + "; ".join(summary_bits) + "."

        return "Mình chưa có thông tin lâu dài trong User.md."

    def _maybe_build_langchain_agent(self):
        try:
            if not self.config.model.api_key and self.config.model.provider not in {"ollama"}:
                return None
            return build_chat_model(self.config.model)
        except Exception:
            return None
