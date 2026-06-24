"""LangGraph multi-agent workflow orchestration."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langsmith import traceable

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.state_adapter import (
    WorkflowState,
    from_workflow_state,
    to_workflow_state,
)
from multi_agent_research_lab.observability.tracing import configure_tracing, trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class MultiAgentWorkflow:
    """Builds and runs a compiled LangGraph supervisor loop."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()
        self._supervisor = SupervisorAgent()
        self._workers = {
            "researcher": ResearcherAgent(self._llm),
            "analyst": AnalystAgent(self._llm),
            "writer": WriterAgent(self._llm),
        }
        self._compiled: CompiledStateGraph | None = None

    def describe_graph(self) -> dict[str, object]:
        """Human-readable graph structure for docs and UI."""

        return {
            "engine": "langgraph",
            "nodes": ["supervisor", "researcher", "analyst", "writer"],
            "edges": [
                "START -> supervisor",
                "supervisor -> researcher | analyst | writer | END",
                "researcher -> supervisor",
                "analyst -> supervisor",
                "writer -> supervisor",
            ],
        }

    def _supervisor_node(self, state: WorkflowState) -> WorkflowState:
        research = from_workflow_state(state)
        updated = self._supervisor.run(research)
        return to_workflow_state(updated)

    def _worker_node(self, role: str):
        def _run(state: WorkflowState) -> WorkflowState:
            research = from_workflow_state(state)
            worker = self._workers.get(role)
            if worker is None:
                research.errors.append(f"Unknown worker: {role}")
                return to_workflow_state(research)
            try:
                updated = worker.run(research)
            except Exception as exc:
                research.errors.append(f"{role} failed: {exc}")
                if role != "writer" and research.research_notes:
                    try:
                        updated = self._workers["writer"].run(research)
                        return to_workflow_state(updated)
                    except Exception as fallback_exc:
                        research.errors.append(f"writer fallback failed: {fallback_exc}")
                return to_workflow_state(research)
            return to_workflow_state(updated)

        return _run

    def _route_after_supervisor(self, state: WorkflowState) -> str:
        if not state["route_history"]:
            return END
        route = state["route_history"][-1]
        if route == "done":
            return END
        settings = get_settings()
        if state["iteration"] >= settings.max_iterations:
            return END
        if route not in self._workers:
            return END
        return route

    def build(self) -> CompiledStateGraph:
        """Compile the LangGraph StateGraph."""

        if self._compiled is not None:
            return self._compiled

        graph = StateGraph(WorkflowState)
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("researcher", self._worker_node("researcher"))
        graph.add_node("analyst", self._worker_node("analyst"))
        graph.add_node("writer", self._worker_node("writer"))

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                END: END,
            },
        )
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")

        self._compiled = graph.compile()
        return self._compiled

    def get_mermaid_diagram(self) -> str:
        """Return Mermaid diagram from the compiled LangGraph."""

        try:
            return self.build().get_graph().draw_mermaid()
        except Exception:
            return (
                "flowchart TD\n"
                "    START --> supervisor\n"
                "    supervisor --> researcher\n"
                "    supervisor --> analyst\n"
                "    supervisor --> writer\n"
                "    supervisor --> END\n"
                "    researcher --> supervisor\n"
                "    analyst --> supervisor\n"
                "    writer --> supervisor"
            )

    @traceable(run_type="chain", name="multi_agent_workflow")
    def run(self, state: ResearchState) -> ResearchState:
        """Execute the compiled graph and return final state."""

        settings = get_settings()
        tracing = configure_tracing(settings)
        if tracing.enabled:
            state.add_trace_event(
                "langsmith",
                {
                    "project": tracing.project,
                    "dashboard_url": tracing.dashboard_url,
                },
            )

        compiled = self.build()
        with trace_span("multi_agent_workflow", {"query": state.request.query}):
            result = compiled.invoke(
                to_workflow_state(state),
                config={"recursion_limit": settings.max_iterations * 2},
            )
            final = from_workflow_state(result)

            if not final.final_answer and not final.errors:
                final.errors.append("Workflow ended without a final answer")

        return final
