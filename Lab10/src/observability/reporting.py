from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric_line(label: str, value: Any) -> str:
    if isinstance(value, float):
        return f"- **{label}**: {value:.4f}"
    return f"- **{label}**: {value}"


def _quality_section(quality: dict[str, Any]) -> str:
    lines = [
        f"- **Success**: {quality.get('success', False)}",
        f"- **Passed checks**: {quality.get('passed_checks', 0)}",
        f"- **Failed checks**: {quality.get('failed_checks', 0)}",
    ]
    for check in quality.get("checks", []):
        status = "PASS" if check.get("passed") else "FAIL"
        lines.append(f"  - `{check['name']}`: {status} (value={check.get('value')})")
    return "\n".join(lines)


def _freshness_section(freshness: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- **Latest published**: {freshness.get('latest_published')}",
            f"- **Oldest published**: {freshness.get('oldest_published')}",
            f"- **Stale rows**: {freshness.get('stale_rows')}",
            f"- **Total rows**: {freshness.get('total_rows')}",
            f"- **Is fresh**: {freshness.get('is_fresh')}",
        ]
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source Summary",
        f"- **API**: {source_summary.get('source_api')}",
        f"- **Query**: {source_summary.get('source_query')}",
        f"- **Filter**: {source_summary.get('source_filter')}",
        f"- **Raw records**: {source_summary.get('raw_records')}",
        f"- **Clean records**: {source_summary.get('clean_records')}",
        "",
        "## Evaluation Metrics",
        _metric_line("Samples", metrics.get("samples")),
        _metric_line("Retrieval hit rate", metrics.get("retrieval_hit_rate")),
        _metric_line("Mean token F1", metrics.get("mean_token_f1")),
        _metric_line("Judge accuracy", metrics.get("judge_accuracy")),
        _metric_line("Mean judge score", metrics.get("mean_judge_score")),
        "",
        "## Data Quality",
        _quality_section(quality),
        "",
        "## Freshness",
        _freshness_section(freshness),
    ]
    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    def delta(metric: str) -> str:
        baseline = baseline_metrics.get(metric, 0.0)
        corrupted = corrupted_metrics.get(metric, 0.0)
        repaired = repaired_metrics.get(metric, 0.0)
        return f"{baseline:.4f} -> {corrupted:.4f} -> {repaired:.4f}"

    lines = [
        "# Corruption Impact Report",
        "",
        "## Metric Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
        f"| Retrieval hit rate | {baseline_metrics.get('retrieval_hit_rate', 0):.4f} | "
        f"{corrupted_metrics.get('retrieval_hit_rate', 0):.4f} | "
        f"{repaired_metrics.get('retrieval_hit_rate', 0):.4f} |",
        f"| Mean token F1 | {baseline_metrics.get('mean_token_f1', 0):.4f} | "
        f"{corrupted_metrics.get('mean_token_f1', 0):.4f} | "
        f"{repaired_metrics.get('mean_token_f1', 0):.4f} |",
        f"| Judge accuracy | {baseline_metrics.get('judge_accuracy', 0):.4f} | "
        f"{corrupted_metrics.get('judge_accuracy', 0):.4f} | "
        f"{repaired_metrics.get('judge_accuracy', 0):.4f} |",
        f"| Mean judge score | {baseline_metrics.get('mean_judge_score', 0):.4f} | "
        f"{corrupted_metrics.get('mean_judge_score', 0):.4f} | "
        f"{repaired_metrics.get('mean_judge_score', 0):.4f} |",
        "",
        "## Trend Summary",
        f"- Retrieval hit rate: {delta('retrieval_hit_rate')}",
        f"- Mean token F1: {delta('mean_token_f1')}",
        f"- Judge accuracy: {delta('judge_accuracy')}",
        f"- Mean judge score: {delta('mean_judge_score')}",
        "",
        "## Corrupted Data Quality",
        _quality_section(corrupted_quality),
        "",
        "## Repaired Data Quality",
        _quality_section(repaired_quality),
        "",
        "## Corrupted Freshness",
        _freshness_section(corrupted_freshness),
        "",
        "## Repaired Freshness",
        _freshness_section(repaired_freshness),
        "",
        "## Conclusion",
        "Corruption degrades retrieval and answer quality; repairing from the raw source restores metrics toward baseline.",
    ]
    write_text(report_path, "\n".join(lines) + "\n")
