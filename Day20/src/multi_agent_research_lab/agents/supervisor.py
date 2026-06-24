"""Supervisor / router."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def decide(self, state: ResearchState) -> str:
        """Return next route: researcher, analyst, writer, or done."""

        if state.final_answer:
            return "done"
        if not state.research_notes:
            return "researcher"
        if not state.analysis_notes:
            return "analyst"
        return "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Record the next route in `state.route_history`."""

        settings = get_settings()
        with trace_span("supervisor", {"iteration": state.iteration}) as span:
            if state.iteration >= settings.max_iterations:
                state.errors.append("Max iterations reached before completion")
                route = "done"
            else:
                route = self.decide(state)
                if route == "writer" and state.final_answer:
                    route = "done"

            state.record_route(route)
            span["attributes"]["route"] = route
            state.add_trace_event(
                "supervisor_route", {"route": route, "iteration": state.iteration}
            )
        return state
