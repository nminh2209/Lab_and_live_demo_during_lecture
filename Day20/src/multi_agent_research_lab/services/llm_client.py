"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass

from langsmith import traceable
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError

# gpt-4o-mini pricing (USD per 1M tokens) — update if model changes.
_INPUT_COST_PER_M = 0.15
_OUTPUT_COST_PER_M = 0.60


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


def _estimate_cost(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    return (input_tokens or 0) * _INPUT_COST_PER_M / 1_000_000 + (
        output_tokens or 0
    ) * _OUTPUT_COST_PER_M / 1_000_000


class LLMClient:
    """Provider-agnostic LLM client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.openai_api_key:
            raise AgentExecutionError("OPENAI_API_KEY is not set")
        self._client = OpenAI(
            api_key=self._settings.openai_api_key,
            timeout=float(self._settings.timeout_seconds),
        )

    @traceable(run_type="llm", name="openai_complete")
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion with token usage and estimated cost."""

        try:
            response = self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
        except Exception as exc:
            raise AgentExecutionError(f"LLM call failed: {exc}") from exc

        choice = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        return LLMResponse(
            content=choice.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_estimate_cost(input_tokens, output_tokens),
        )
