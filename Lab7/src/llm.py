from __future__ import annotations

import os
from typing import Callable

OPENAI_LLM_MODEL = "gpt-4o-mini"
LLM_PROVIDER_ENV = "LLM_PROVIDER"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"


def demo_llm(prompt: str) -> str:
    """Deterministic mock LLM for offline demos and tests."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def create_llm_fn(
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
) -> Callable[[str], str]:
    """
    Build an LLM callable for KnowledgeBaseAgent.

    provider: mock | openai (defaults to env LLM_PROVIDER or mock)
    api_key: optional override; falls back to OPENAI_API_KEY env var
    """
    selected = (provider or os.getenv(LLM_PROVIDER_ENV, "mock")).strip().lower()
    if selected != "openai":
        return demo_llm

    resolved_key = (api_key or os.getenv(OPENAI_API_KEY_ENV, "")).strip()
    if not resolved_key:
        raise ValueError(
            "OpenAI LLM selected but no API key found. "
            "Set OPENAI_API_KEY in .env or paste a key in the UI."
        )

    resolved_model = model_name or os.getenv("OPENAI_LLM_MODEL", OPENAI_LLM_MODEL)

    def openai_llm(prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=resolved_key)
        response = client.chat.completions.create(
            model=resolved_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful knowledge assistant. "
                        "Answer only from the provided context. "
                        "Synthesize across chunks when needed. "
                        "If the context describes related ideas (for example, "
                        "types or purposes of a concept), explain from those "
                        "descriptions instead of refusing. "
                        "Say clearly only when the context truly lacks relevant information."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    openai_llm._backend_name = resolved_model  # type: ignore[attr-defined]
    return openai_llm
