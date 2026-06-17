"""LLM client — OpenAI when configured, otherwise mock with safe fallback."""
import logging

from openai import APIConnectionError, APIStatusError, OpenAI

from app.config import settings
from utils.mock_llm import ask as mock_ask

logger = logging.getLogger(__name__)

_last_provider = "mock"


def get_llm_provider() -> str:
    return _last_provider


def ask(question: str, history: list[dict] | None = None) -> tuple[str, int, int, str]:
    """
    Returns: answer, input_tokens, output_tokens, model_label
    """
    global _last_provider
    history = history or []

    if settings.use_mock_llm or not settings.openai_configured:
        _last_provider = "mock"
        answer = mock_ask(question, history=history)
        input_tokens = max(1, len(question.split()) * 2)
        output_tokens = max(1, len(answer.split()) * 2)
        return answer, input_tokens, output_tokens, "mock-llm"

    try:
        result = _ask_openai(question, history)
        _last_provider = "openai"
        return result
    except Exception as exc:
        logger.error("OpenAI request failed: %s", exc)
        if not settings.llm_fallback_mock:
            raise
        logger.warning("Falling back to mock LLM")
        _last_provider = "mock-fallback"
        answer = mock_ask(question, history=history)
        input_tokens = max(1, len(question.split()) * 2)
        output_tokens = max(1, len(answer.split()) * 2)
        return answer, input_tokens, output_tokens, "mock-llm (openai unavailable)"


def _ask_openai(question: str, history: list[dict]) -> tuple[str, int, int, str]:
    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=60.0,
        max_retries=2,
    )
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history[-settings.history_max_messages :]
    ]
    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=500,
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            "Cannot reach OpenAI API from this server. "
            "Check OPENAI_API_KEY or set USE_MOCK_LLM=true on Render."
        ) from exc
    except APIStatusError as exc:
        raise RuntimeError(f"OpenAI API error: {exc.message}") from exc

    answer = response.choices[0].message.content or ""
    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else len(question.split()) * 2
    output_tokens = usage.completion_tokens if usage else len(answer.split()) * 2
    logger.info("OpenAI call model=%s in=%s out=%s", settings.llm_model, input_tokens, output_tokens)
    return answer, input_tokens, output_tokens, settings.llm_model
