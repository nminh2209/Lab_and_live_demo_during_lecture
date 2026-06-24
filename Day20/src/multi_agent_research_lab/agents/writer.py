"""Writer agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        with trace_span("writer") as span:
            source_refs = "\n".join(
                f"- [{i + 1}] {s.title}: {s.url or 'n/a'}" for i, s in enumerate(state.sources)
            )
            response = self._llm.complete(
                system_prompt=(
                    "You are a technical writer. Write a clear ~500-word answer for the audience. "
                    "Include inline citations like [1] and a Sources section at the end."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Research notes:\n{state.research_notes or ''}\n\n"
                    f"Analysis:\n{state.analysis_notes or ''}\n\n"
                    f"Available sources:\n{source_refs}"
                ),
            )
            state.final_answer = response.content
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
                    content=response.content,
                    metadata={
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "cost_usd": response.cost_usd,
                    },
                )
            )
            span["attributes"]["answer_length"] = len(response.content)
            state.add_trace_event("writer_complete", {"answer_length": len(response.content)})
        return state
