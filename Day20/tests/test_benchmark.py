"""Tests for benchmark quality judge and failure-rate suite."""

from unittest.mock import MagicMock

from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    measure_failure_rate,
    score_quality_llm,
)
from multi_agent_research_lab.services.llm_client import LLMResponse


def test_score_quality_llm_parses_json() -> None:
    state = ResearchState(
        request=ResearchQuery(query="Explain GraphRAG"),
        final_answer="GraphRAG combines knowledge graphs with retrieval.",
    )
    llm = MagicMock()
    llm.complete.return_value = LLMResponse(content='{"score": 8.5, "rationale": "solid"}')
    assert score_quality_llm(state, llm) == 8.5


def test_measure_failure_rate() -> None:
    def flaky_runner(query: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=query))
        if "fail" in query:
            state.errors.append("boom")
        else:
            state.final_answer = "ok"
        return state

    rate = measure_failure_rate(
        ["good query here", "this will fail now", "another good query"],
        flaky_runner,
    )
    assert rate == 1 / 3
