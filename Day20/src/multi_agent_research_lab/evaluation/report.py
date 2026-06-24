"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics, BenchmarkSuiteResult


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    *,
    query: str = "",
    reflection: str = "",
    suite: BenchmarkSuiteResult | None = None,
) -> str:
    """Render benchmark metrics to markdown with optional reflection."""

    lines = [
        "# Benchmark Report",
        "",
        f"**Query:** {query}" if query else "",
        "",
        "## Metrics",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality (0-10) | Citations | Failure rate | Notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        citations = "" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        method = f" ({item.quality_method})" if item.quality_method else ""
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | "
            f"{quality}{method} | {citations} | {failure} | {item.notes} |"
        )

    if suite is not None:
        lines.extend(
            [
                "",
                "## Batch failure rate",
                "",
                f"Measured over **{suite.suite_query_count}** suite queries "
                "(lab guide: failed queries / total queries).",
                "",
                "| Mode | Failure rate |",
                "|---|---:|",
                f"| Baseline | {suite.baseline_suite_failure_rate:.0%} |",
                f"| Multi-agent | {suite.multi_agent_suite_failure_rate:.0%} |",
            ]
        )

    if len(metrics) >= 2:
        baseline = metrics[0]
        multi = metrics[1]
        lines.extend(
            [
                "",
                "## Comparison",
                "",
                f"- **Latency delta:** {multi.latency_seconds - baseline.latency_seconds:+.2f}s "
                f"(multi-agent vs baseline)",
            ]
        )
        if baseline.estimated_cost_usd and multi.estimated_cost_usd:
            lines.append(
                f"- **Cost delta:** ${multi.estimated_cost_usd - baseline.estimated_cost_usd:+.4f}"
            )
        if baseline.quality_score is not None and multi.quality_score is not None:
            lines.append(
                f"- **Quality delta:** {multi.quality_score - baseline.quality_score:+.1f} points "
                f"(scored via {baseline.quality_method})"
            )
        if baseline.citation_coverage is not None and multi.citation_coverage is not None:
            lines.append(
                f"- **Citation coverage delta:** "
                f"{multi.citation_coverage - baseline.citation_coverage:+.0%}"
            )

    if reflection:
        lines.extend(["", "## Reflection", "", reflection])

    return "\n".join(line for line in lines if line is not None) + "\n"
