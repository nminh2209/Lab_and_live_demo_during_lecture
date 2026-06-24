"""Run README-lec prompts through the existing research pipeline with full logging."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    compute_state_metrics,
    run_baseline,
    run_benchmark,
    run_multi_agent,
)
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_tracing

PROMPTS_DIR = Path("prompts")
DEFAULT_LOG = Path("reports/lec_integration_run.log")


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _section(title: str) -> str:
    bar = "=" * 72
    return f"\n{bar}\n{title}\n{bar}\n"


def _format_metrics(metrics: BenchmarkMetrics) -> str:
    return (
        f"latency={metrics.latency_seconds:.1f}s | "
        f"cost=${metrics.estimated_cost_usd or 0:.4f} | "
        f"quality={metrics.quality_score} ({metrics.quality_method}) | "
        f"citations={metrics.citation_coverage:.0%} | notes={metrics.notes}"
    )


def _format_state_summary(state: ResearchState) -> str:
    m = compute_state_metrics(state)
    lines = [
        f"sources={m['source_count']} | llm_calls={m['llm_calls']} | errors={m['error_count']}",
        f"routes={state.route_history}",
        f"research_notes_chars={len(state.research_notes or '')}",
        f"analysis_notes_chars={len(state.analysis_notes or '')}",
        f"final_answer_chars={len(state.final_answer or '')}",
    ]
    if state.errors:
        lines.append(f"last_error={state.errors[-1]}")
    return "\n".join(lines)


def run_prompt(
    prompt_path: Path,
    *,
    mode: str = "both",
    log_path: Path = DEFAULT_LOG,
) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    tracing = configure_tracing(settings)

    query = _read_prompt(prompt_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    chunks: list[str] = [
        _section(f"LECTURE PROMPT RUN — {prompt_path.name} — {datetime.now(UTC).isoformat()}"),
        f"prompt_file: {prompt_path.resolve()}",
        f"log_file: {log_path.resolve()}",
        f"langsmith: {tracing.dashboard_url if tracing.enabled else 'disabled'}",
        f"tavily: {'enabled' if tracing.tavily_enabled else 'mock'}",
        "\n--- PROMPT TEXT ---\n",
        query,
    ]

    llm = None  # let benchmark helpers construct client

    if mode in ("baseline", "both"):
        chunks.append(_section("BASELINE (single-agent)"))
        baseline = run_benchmark("lec-baseline", query, run_baseline, llm=llm)
        chunks.append(_format_metrics(baseline.metrics))
        chunks.append("\n--- state summary ---\n")
        chunks.append(_format_state_summary(baseline.state))
        chunks.append("\n--- final_answer ---\n")
        chunks.append(baseline.state.final_answer or "(empty)")

    if mode in ("multi-agent", "both"):
        chunks.append(_section("MULTI-AGENT (supervisor → researcher → analyst → writer)"))
        multi = run_benchmark("lec-multi-agent", query, run_multi_agent, llm=llm)
        chunks.append(_format_metrics(multi.metrics))
        chunks.append("\n--- state summary ---\n")
        chunks.append(_format_state_summary(multi.state))
        if multi.state.research_notes:
            chunks.append("\n--- research_notes (excerpt) ---\n")
            chunks.append(multi.state.research_notes[:2500])
        if multi.state.analysis_notes:
            chunks.append("\n--- analysis_notes (excerpt) ---\n")
            chunks.append(multi.state.analysis_notes[:2500])
        chunks.append("\n--- final_answer ---\n")
        chunks.append(multi.state.final_answer or "(empty)")
        chunks.append("\n--- trace events ---\n")
        chunks.append(json.dumps(multi.state.trace, indent=2))

    log_path.write_text("\n".join(chunks), encoding="utf-8")
    print(f"Wrote full log to {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt",
        nargs="?",
        default=str(PROMPTS_DIR / "lec02_research_briefing.txt"),
        help="Path to a lecture prompt text file",
    )
    parser.add_argument(
        "--mode",
        choices=("baseline", "multi-agent", "both"),
        default="both",
    )
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()
    run_prompt(Path(args.prompt), mode=args.mode, log_path=args.log)


if __name__ == "__main__":
    main()
