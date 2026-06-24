"""Researcher agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, llm: LLMClient | None = None, search: SearchClient | None = None) -> None:
        self._llm = llm or LLMClient()
        self._search = search or SearchClient(self._llm)

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        with trace_span("researcher", {"query": state.request.query}) as span:
            sources = self._search.search(
                state.request.query, max_results=state.request.max_sources
            )
            state.sources = sources
            provider = self._search.provider

            source_block = "\n\n".join(
                f"[{i + 1}] {s.title}\nURL: {s.url or 'n/a'}\n{s.snippet}"
                for i, s in enumerate(sources)
            )
            response = self._llm.complete(
                system_prompt=(
                    "You are a research assistant. Summarize the provided sources into structured "
                    "research notes. Include key facts and cite sources as [1], [2], etc."
                ),
                user_prompt=f"Query: {state.request.query}\n\nSources:\n{source_block}",
            )
            state.research_notes = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                        "source_count": len(sources),
                    },
                )
            )
            span["attributes"]["source_count"] = len(sources)
            span["attributes"]["search_provider"] = provider
            state.add_trace_event(
                "researcher_complete",
                {"notes_length": len(response.content), "search_provider": provider},
            )
        return state
