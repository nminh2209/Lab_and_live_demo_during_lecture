"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError, StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    run_baseline,
    run_benchmark_suite,
    save_benchmark_artifact,
)
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_tracing

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    tracing = configure_tracing(settings)
    if tracing.enabled:
        console.print(f"LangSmith tracing: {tracing.dashboard_url}")
    if tracing.tavily_enabled:
        console.print("Web search: Tavily")
    else:
        console.print("Web search: LLM mock (set TAVILY_API_KEY for real search)")


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run single-agent baseline with a real LLM call."""

    _init()
    try:
        state = run_baseline(query)
    except AgentExecutionError as exc:
        console.print(Panel.fit(str(exc), title="Error", style="red"))
        raise typer.Exit(code=1) from exc

    cost = sum(
        float(r.metadata["cost_usd"])
        for r in state.agent_results
        if r.metadata.get("cost_usd") is not None
    )
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))
    console.print(f"Latency tokens logged in trace; estimated cost: ${cost:.4f}")


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except (StudentTodoError, AgentExecutionError) as exc:
        console.print(Panel.fit(str(exc), title="Error", style="red"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Research query",
        ),
    ] = "Research GraphRAG state-of-the-art and write a 500-word summary",
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Markdown report path"),
    ] = Path("reports/benchmark_report.md"),
) -> None:
    """Run baseline vs multi-agent benchmark and write a report."""

    _init()
    console.print(f"Running benchmark for: {query}")
    console.print("Step 1/2: primary query comparison (LLM quality judge)...")

    suite_result = run_benchmark_suite(query)
    baseline_metrics = suite_result.baseline
    multi_metrics = suite_result.multi_agent
    baseline_state = ResearchState.model_validate(suite_result.baseline_state)
    multi_state = ResearchState.model_validate(suite_result.multi_agent_state)

    console.print(
        f"  baseline: {baseline_metrics.latency_seconds:.1f}s, "
        f"quality={baseline_metrics.quality_score:.1f} ({baseline_metrics.quality_method})"
    )
    console.print(
        f"  multi-agent: {multi_metrics.latency_seconds:.1f}s, "
        f"quality={multi_metrics.quality_score:.1f} ({multi_metrics.quality_method})"
    )
    console.print(
        f"Step 2/2: suite failure rate (n={suite_result.suite_query_count}) — "
        f"baseline {suite_result.baseline_suite_failure_rate:.0%}, "
        f"multi-agent {suite_result.multi_agent_suite_failure_rate:.0%}"
    )

    reflection = _build_reflection(baseline_state, multi_state, baseline_metrics, multi_metrics)
    report = render_markdown_report(
        [baseline_metrics, multi_metrics],
        query=query,
        reflection=reflection,
        suite=suite_result,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    artifact_path = output.parent / "last_benchmark.json"
    save_benchmark_artifact(suite_result, artifact_path)
    console.print(
        Panel.fit(
            f"Report: {output}\nArtifact: {artifact_path}",
            title="Benchmark complete",
            style="green",
        )
    )


def _build_reflection(
    baseline_state: ResearchState,
    multi_state: ResearchState,
    baseline_metrics: object,
    multi_metrics: object,
) -> str:
    from multi_agent_research_lab.core.schemas import BenchmarkMetrics

    assert isinstance(baseline_metrics, BenchmarkMetrics)
    assert isinstance(multi_metrics, BenchmarkMetrics)

    lines = [
        "### When multi-agent helps",
        "",
        "Multi-agent shines when tasks decompose cleanly — research, analysis, and writing "
        "benefit from specialized prompts and intermediate artifacts (`research_notes`, "
        "`analysis_notes`) that make debugging and citation tracking easier.",
        "",
        "### When single-agent is enough",
        "",
        "For straightforward summaries without strict citation requirements, a single well-prompted "
        "call is often faster and cheaper with comparable readability.",
        "",
        "### Observed results (this run)",
        "",
        f"- Baseline: {baseline_metrics.latency_seconds:.1f}s, "
        f"cost=${baseline_metrics.estimated_cost_usd or 0:.4f}, "
        f"quality={baseline_metrics.quality_score:.1f}/10, "
        f"sources={len(baseline_state.sources)}",
        f"- Multi-agent: {multi_metrics.latency_seconds:.1f}s, "
        f"cost=${multi_metrics.estimated_cost_usd or 0:.4f}, "
        f"quality={multi_metrics.quality_score:.1f}/10, "
        f"sources={len(multi_state.sources)}, "
        f"routes={multi_state.route_history}",
        "",
        "### Failure mode & fix",
        "",
    ]

    if multi_state.errors:
        lines.append(
            f"Observed: {multi_state.errors[0]}. "
            "Fix: add retry per agent, fall back to baseline writer on worker failure, "
            "and surface partial results instead of empty output."
        )
    else:
        lines.append(
            "Observed: multi-agent latency and cost scale with agent count (4+ LLM calls vs 1). "
            "Fix: cache search results, parallelize independent steps, or skip analyst for "
            "simple factual queries."
        )

    return "\n".join(lines)


if __name__ == "__main__":
    app()
