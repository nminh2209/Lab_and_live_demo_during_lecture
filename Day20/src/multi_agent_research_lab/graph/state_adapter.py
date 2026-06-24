"""Convert between Pydantic ResearchState and LangGraph dict state."""

from typing import Any, TypedDict

from multi_agent_research_lab.core.state import ResearchState


class WorkflowState(TypedDict):
    """LangGraph state schema (JSON-serializable dict)."""

    request: dict[str, Any]
    iteration: int
    route_history: list[str]
    sources: list[dict[str, Any]]
    research_notes: str | None
    analysis_notes: str | None
    final_answer: str | None
    agent_results: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    errors: list[str]


def to_workflow_state(state: ResearchState) -> WorkflowState:
    return state.model_dump()  # type: ignore[return-value]


def from_workflow_state(data: WorkflowState) -> ResearchState:
    return ResearchState.model_validate(data)
