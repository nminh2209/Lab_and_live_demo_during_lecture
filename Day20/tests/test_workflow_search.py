"""Tests for LangGraph workflow and search providers."""

from unittest.mock import MagicMock, patch

import pytest

from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.search_client import SearchClient


def test_describe_graph_uses_langgraph() -> None:
    wf = MultiAgentWorkflow.__new__(MultiAgentWorkflow)
    graph = wf.describe_graph()
    assert graph["engine"] == "langgraph"
    assert "supervisor" in graph["nodes"]


def test_search_client_provider_without_tavily(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    client = SearchClient(settings=MagicMock(tavily_api_key=None, openai_api_key="sk-test"))
    assert client.provider == "llm_mock"


def test_search_client_provider_with_tavily(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearchClient(settings=MagicMock(tavily_api_key="tvly-test", openai_api_key="sk-test"))
    assert client.provider == "tavily"


@patch("tavily.TavilyClient")
def test_search_tavily_maps_results(mock_tavily: MagicMock) -> None:
    mock_tavily.return_value.search.return_value = {
        "results": [
            {
                "title": "GraphRAG Paper",
                "url": "https://example.com/graphrag",
                "content": "GraphRAG combines graphs with RAG.",
                "score": 0.9,
            }
        ]
    }
    llm = MagicMock()
    client = SearchClient(
        llm=llm,
        settings=MagicMock(tavily_api_key="tvly-test", openai_api_key="sk-test"),
    )
    sources = client.search("GraphRAG", max_results=3)
    assert len(sources) == 1
    assert sources[0].metadata["provider"] == "tavily"
    llm.complete.assert_not_called()


def test_workflow_builds_compiled_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    wf = MultiAgentWorkflow()
    compiled = wf.build()
    assert compiled is not None
    assert "supervisor" in compiled.get_graph().nodes
