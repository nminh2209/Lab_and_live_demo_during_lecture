"""Search client abstraction for ResearcherAgent."""

import json
import logging
import re

from langsmith import traceable

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class SearchClient:
    """Tavily web search when configured; LLM-backed mock as fallback."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMClient(self._settings)

    @property
    def provider(self) -> str:
        if self._settings.tavily_api_key and self._settings.tavily_api_key.strip():
            return "tavily"
        return "llm_mock"

    @traceable(run_type="tool", name="web_search")
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""

        if self.provider == "tavily":
            try:
                return self._search_tavily(query, max_results)
            except Exception as exc:
                logger.warning("Tavily search failed, falling back to LLM mock: %s", exc)

        return self._search_llm_mock(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        from tavily import TavilyClient

        client = TavilyClient(api_key=self._settings.tavily_api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
        )
        sources: list[SourceDocument] = []
        for item in response.get("results", []):
            sources.append(
                SourceDocument(
                    title=str(item.get("title", "Untitled")),
                    url=item.get("url"),
                    snippet=str(item.get("content", ""))[:1500],
                    metadata={
                        "provider": "tavily",
                        "score": item.get("score"),
                    },
                )
            )
        if not sources:
            raise ValueError("Tavily returned no results")
        return sources

    def _search_llm_mock(self, query: str, max_results: int) -> list[SourceDocument]:
        response = self._llm.complete(
            system_prompt=(
                "You simulate a web search API. Return ONLY a JSON array of objects with keys: "
                "title (string), url (string), snippet (string). "
                "Use realistic URLs and concise snippets. "
                "No markdown fences or extra text."
            ),
            user_prompt=f"Search query: {query}\nMax results: {max_results}",
        )
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = [
                {
                    "title": f"Overview: {query[:60]}",
                    "url": "https://example.com/research",
                    "snippet": raw[:500],
                }
            ]

        sources: list[SourceDocument] = []
        for item in items[:max_results]:
            if not isinstance(item, dict):
                continue
            sources.append(
                SourceDocument(
                    title=str(item.get("title", "Untitled")),
                    url=item.get("url"),
                    snippet=str(item.get("snippet", "")),
                    metadata={"provider": "llm_mock"},
                )
            )
        return sources
