"""Benchmark for single-agent vs multi-agent."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from langsmith import traceable

from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    BenchmarkMetrics,
    BenchmarkSuiteResult,
    ResearchQuery,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.tracing import configure_tracing, trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

Runner = Callable[[str], ResearchState]

_CITATION_PATTERN = re.compile(r"\[\d+\]|https?://\S+")
_SCORE_PATTERN = re.compile(r"\b(10(?:\.0+)?|[0-9](?:\.\d+)?)\b")

DEFAULT_BENCHMARK_SUITE = [
    "Research GraphRAG state-of-the-art and write a 500-word summary",
    "Compare RAG vs fine-tuning for enterprise knowledge bases",
    "Summarize recent advances in multi-agent LLM orchestration",
]


@dataclass(frozen=True)
class BenchmarkRunResult:
    state: ResearchState
    metrics: BenchmarkMetrics


def _sum_cost(state: ResearchState) -> float | None:
    costs = [r.metadata.get("cost_usd") for r in state.agent_results if r.metadata.get("cost_usd")]
    return sum(float(c) for c in costs) if costs else None


def citation_coverage(state: ResearchState) -> float:
    if not state.final_answer or not state.sources:
        return 0.0
    citations = len(_CITATION_PATTERN.findall(state.final_answer))
    return min(1.0, citations / max(len(state.sources), 1))


def _heuristic_quality(state: ResearchState) -> float:
    """Lightweight 0-10 score from structure, length, citations, and errors."""

    if not state.final_answer:
        return 0.0
    score = 5.0
    word_count = len(state.final_answer.split())
    if word_count >= 300:
        score += 1.5
    elif word_count >= 150:
        score += 0.5
    score += citation_coverage(state) * 2.0
    if state.sources:
        score += 0.5
    if state.analysis_notes:
        score += 0.5
    score -= min(3.0, len(state.errors) * 1.5)
    return max(0.0, min(10.0, score))


@traceable(run_type="llm", name="quality_judge")
def score_quality_llm(state: ResearchState, llm: LLMClient) -> float | None:
    """LLM peer-review rubric score (0–10) aligned with lab grading."""

    if not state.final_answer:
        return 0.0

    response = llm.complete(
        system_prompt=(
            "You are a strict peer reviewer for a research assistant lab. "
            "Score the answer from 0 to 10 using: role clarity of content, factual structure, "
            "citation use, completeness vs the query. "
            'Reply with ONLY valid JSON: {"score": <number>, "rationale": "..."}'
        ),
        user_prompt=(
            f"Query: {state.request.query}\n\n"
            f"Answer:\n{state.final_answer[:6000]}\n\n"
            f"Sources available: {len(state.sources)}"
        ),
    )
    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        payload = json.loads(raw)
        score = float(payload["score"])
        return max(0.0, min(10.0, score))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        match = _SCORE_PATTERN.search(response.content)
        if match:
            return max(0.0, min(10.0, float(match.group(1))))
    return None


def _resolve_quality(state: ResearchState, llm: LLMClient | None) -> tuple[float, str]:
    if llm is not None:
        judged = score_quality_llm(state, llm)
        if judged is not None:
            return judged, "llm_judge"
    return _heuristic_quality(state), "heuristic"


def _is_failed_run(state: ResearchState) -> bool:
    return bool(state.errors) or not state.final_answer


def measure_failure_rate(
    queries: list[str],
    runner: Runner,
) -> float:
    """Fraction of queries that fail (errors or empty final answer)."""

    if not queries:
        return 0.0
    failures = 0
    for query in queries:
        try:
            state = runner(query)
            if _is_failed_run(state):
                failures += 1
        except Exception:
            failures += 1
    return failures / len(queries)


@traceable(run_type="chain", name="single_agent_baseline")
def run_baseline(query: str, llm: LLMClient | None = None) -> ResearchState:
    """Single-agent baseline: one LLM call does research + writing."""

    configure_tracing()
    client = llm or LLMClient()
    state = ResearchState(request=ResearchQuery(query=query))
    with trace_span("baseline"):
        response = client.complete(
            system_prompt=(
                "You are a research assistant. Research the topic and write a ~500-word technical "
                "summary with inline citations [1], [2] and a Sources section."
            ),
            user_prompt=query,
        )
        state.final_answer = response.content
        state.agent_results.append(
            AgentResult(
                agent=AgentName.SUPERVISOR,
                content=response.content,
                metadata={
                    "mode": "baseline",
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("baseline_complete", {"answer_length": len(response.content)})
    return state


def run_multi_agent(query: str, llm: LLMClient | None = None) -> ResearchState:
    """Multi-agent workflow runner."""

    return MultiAgentWorkflow(llm).run(ResearchState(request=ResearchQuery(query=query)))


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
    *,
    llm: LLMClient | None = None,
    failure_rate: float | None = None,
) -> BenchmarkRunResult:
    """Measure latency, cost, citation coverage, and LLM-judged quality."""

    started = perf_counter()
    failed = False
    try:
        state = runner(query)
    except Exception as exc:
        state = ResearchState(request=ResearchQuery(query=query))
        state.errors.append(str(exc))
        failed = True
    latency = perf_counter() - started

    judge_llm = llm or LLMClient()
    quality, quality_method = _resolve_quality(state, judge_llm)
    coverage = citation_coverage(state)
    cost = _sum_cost(state)

    state.add_trace_event(
        "benchmark_metrics",
        {
            "quality_score": quality,
            "quality_method": quality_method,
            "citation_coverage": coverage,
            "failure_rate": failure_rate,
        },
    )

    notes = (
        f"citation_coverage={coverage:.0%}; quality_method={quality_method}; "
        f"errors={len(state.errors)}; failed={'yes' if failed else 'no'}"
    )
    if failure_rate is not None:
        notes += f"; suite_failure_rate={failure_rate:.0%}"
    if state.errors:
        notes += f"; last_error={state.errors[-1][:80]}"

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=quality,
        citation_coverage=coverage,
        failure_rate=failure_rate,
        quality_method=quality_method,
        notes=notes,
    )
    return BenchmarkRunResult(state=state, metrics=metrics)


@traceable(run_type="chain", name="benchmark_suite")
def run_benchmark_suite(
    query: str,
    *,
    suite_queries: list[str] | None = None,
    llm: LLMClient | None = None,
) -> BenchmarkSuiteResult:
    """Primary comparison plus batch failure rates over a query suite."""

    client = llm or LLMClient()
    suite = suite_queries or DEFAULT_BENCHMARK_SUITE

    baseline = run_benchmark(
        "single-agent-baseline",
        query,
        run_baseline,
        llm=client,
    )
    multi = run_benchmark(
        "multi-agent",
        query,
        run_multi_agent,
        llm=client,
    )

    baseline_fail = measure_failure_rate(suite, run_baseline)
    multi_fail = measure_failure_rate(suite, run_multi_agent)

    baseline_metrics = baseline.metrics.model_copy(
        update={
            "failure_rate": baseline_fail,
            "notes": (
                f"{baseline.metrics.notes}; suite_failure_rate={baseline_fail:.0%} (n={len(suite)})"
            ),
        }
    )
    multi_metrics = multi.metrics.model_copy(
        update={
            "failure_rate": multi_fail,
            "notes": (
                f"{multi.metrics.notes}; suite_failure_rate={multi_fail:.0%} (n={len(suite)})"
            ),
        }
    )

    return BenchmarkSuiteResult(
        query=query,
        baseline=baseline_metrics,
        multi_agent=multi_metrics,
        baseline_state=json.loads(baseline.state.model_dump_json()),
        multi_agent_state=json.loads(multi.state.model_dump_json()),
        suite_query_count=len(suite),
        baseline_suite_failure_rate=baseline_fail,
        multi_agent_suite_failure_rate=multi_fail,
    )


def save_benchmark_artifact(suite: BenchmarkSuiteResult, path: Path) -> None:
    """Persist suite results for Streamlit and deliverables."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(suite.model_dump_json(indent=2), encoding="utf-8")


def load_benchmark_artifact(path: Path) -> BenchmarkSuiteResult | None:
    if not path.is_file():
        return None
    try:
        return BenchmarkSuiteResult.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def apply_suite_to_session(suite: BenchmarkSuiteResult) -> tuple[ResearchState, ResearchState]:
    baseline_state = ResearchState.model_validate(suite.baseline_state)
    multi_state = ResearchState.model_validate(suite.multi_agent_state)
    return baseline_state, multi_state


def compute_state_metrics(state: ResearchState) -> dict[str, float | int | str | None]:
    """Public helpers for UIs and reports."""

    benchmark_event = next(
        (e for e in state.trace if e.get("name") == "benchmark_metrics"),
        None,
    )
    payload = benchmark_event.get("payload", {}) if benchmark_event else {}

    return {
        "cost_usd": _sum_cost(state),
        "citation_coverage": payload.get("citation_coverage", citation_coverage(state)),
        "quality_score": payload.get("quality_score", _heuristic_quality(state)),
        "quality_method": payload.get("quality_method", "heuristic"),
        "failure_rate": payload.get("failure_rate"),
        "source_count": len(state.sources),
        "error_count": len(state.errors),
        "llm_calls": len(state.agent_results),
    }
