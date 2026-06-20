from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@dataclass
class ExtractedFact:
    key: str
    value: str
    confidence: float
    is_correction: bool = False


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int


def usage_from_response(response) -> TokenUsage:
    meta = getattr(response, "usage_metadata", None) or {}
    prompt = int(meta.get("input_tokens") or meta.get("prompt_tokens") or 0)
    completion = int(meta.get("output_tokens") or meta.get("completion_tokens") or 0)

    if prompt == 0 and completion == 0:
        response_meta = getattr(response, "response_metadata", {}) or {}
        token_usage = response_meta.get("token_usage") or {}
        prompt = int(token_usage.get("prompt_tokens") or 0)
        completion = int(token_usage.get("completion_tokens") or 0)

    return TokenUsage(prompt_tokens=prompt, completion_tokens=completion)


def extract_facts_with_llm(llm, message: str) -> list[ExtractedFact]:
    system = SystemMessage(
        content=(
            "You extract stable user profile facts from Vietnamese chat messages. "
            "Return ONLY valid JSON: "
            '{"facts":[{"key":"name|location|profession|response_style|favorite_drink|favorite_food|pet|interests",'
            '"value":"...", "confidence":0.0-1.0, "is_correction":false}]}. '
            "Rules: skip pure questions; ignore jokes/noise; mark is_correction=true for đính chính/cập nhật; "
            "confidence >= 0.9 for explicit self-identification, 0.5-0.8 for inferred facts."
        )
    )
    human = HumanMessage(content=message)
    response = llm.invoke([system, human])
    raw = str(response.content).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    facts: list[ExtractedFact] = []
    for item in payload.get("facts", []):
        key = str(item.get("key", "")).strip().lower()
        value = str(item.get("value", "")).strip()
        if not key or not value:
            continue
        facts.append(
            ExtractedFact(
                key=key,
                value=value,
                confidence=float(item.get("confidence", 0.0)),
                is_correction=bool(item.get("is_correction", False)),
            )
        )
    return facts


def summarize_with_llm(llm, messages: list[dict[str, str]]) -> str:
    if not messages:
        return ""
    transcript = "\n".join(f"{item['role']}: {item['content']}" for item in messages)
    system = SystemMessage(
        content=(
            "Summarize older Vietnamese chat turns into a compact bullet summary. "
            "Keep stable user facts, preferences, and corrections. Max 120 words."
        )
    )
    human = HumanMessage(content=transcript)
    response = llm.invoke([system, human])
    return str(response.content).strip()


def build_baseline_messages(session_messages: list[dict[str, str]]) -> list:
    system = SystemMessage(
        content=(
            "You are a helpful Vietnamese assistant. "
            "You only remember the current conversation thread (no long-term memory). "
            "Be concise and practical."
        )
    )
    messages = [system]
    for item in session_messages:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    return messages


def build_advanced_messages(
    profile_text: str,
    summary: str,
    recent_messages: list[dict[str, str]],
) -> list:
    system = SystemMessage(
        content=(
            "You are an advanced Vietnamese assistant with persistent User.md memory "
            "and compact thread memory.\n\n"
            f"User.md:\n{profile_text}\n\n"
            f"Compact summary of older turns:\n{summary or '(none)'}\n\n"
            "Use User.md for cross-session recall. Prefer corrected facts over older ones. "
            "Answer in the user's preferred style when known."
        )
    )
    messages = [system]
    for item in recent_messages:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    return messages
