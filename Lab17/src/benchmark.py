from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tabulate import tabulate

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def recall_points(answer: str, expected: list[str]) -> float:
    if not expected:
        return 1.0
    normalized = answer.lower()
    hits = sum(1 for item in expected if item.lower() in normalized)
    if hits == len(expected):
        return 1.0
    if hits == 0:
        return 0.0
    return 0.5


def heuristic_quality(answer: str, expected: list[str]) -> float:
    if not answer.strip():
        return 0.0
    recall = recall_points(answer, expected)
    length_bonus = 0.2 if 20 <= len(answer) <= 280 else 0.0
    return min(1.0, recall + length_bonus)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    total_agent_tokens = 0
    total_prompt_tokens = 0
    recall_scores: list[float] = []
    quality_scores: list[float] = []
    total_compactions = 0
    memory_growth = 0

    for conversation in conversations:
        user_id = conversation["user_id"]
        conv_id = conversation["id"]
        thread_id = conv_id

        if isinstance(agent, AdvancedAgent):
            memory_before = agent.memory_file_size(user_id)
        else:
            memory_before = 0

        for turn in conversation.get("turns", []):
            result = agent.reply(user_id, thread_id, turn)
            total_agent_tokens += int(result.get("agent_tokens") or 0)
            total_prompt_tokens += int(result.get("prompt_tokens") or 0)

        if isinstance(agent, AdvancedAgent):
            memory_after = agent.memory_file_size(user_id)
            memory_growth += max(0, memory_after - memory_before)
            total_compactions += agent.compaction_count(thread_id)

        for question in conversation.get("recall_questions", []):
            recall_thread = f"{conv_id}-recall"
            result = agent.reply(user_id, recall_thread, question["question"])
            answer = result.get("answer", "")
            expected = question.get("expected_contains", [])
            recall_scores.append(recall_points(answer, expected))
            quality_scores.append(heuristic_quality(answer, expected))
            total_agent_tokens += int(result.get("agent_tokens") or 0)
            total_prompt_tokens += int(result.get("prompt_tokens") or 0)

    count = max(len(recall_scores), 1)
    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=sum(recall_scores) / count,
        response_quality=sum(quality_scores) / count,
        memory_growth_bytes=memory_growth,
        compactions=total_compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    table = [
        [
            row.agent_name,
            row.agent_tokens_only,
            row.prompt_tokens_processed,
            f"{row.recall_score:.2f}",
            f"{row.response_quality:.2f}",
            row.memory_growth_bytes,
            row.compactions,
        ]
        for row in rows
    ]
    headers = [
        "Agent",
        "Agent tokens only",
        "Prompt tokens processed",
        "Cross-session recall",
        "Response quality",
        "Memory growth (bytes)",
        "Compactions",
    ]
    return tabulate(table, headers=headers, tablefmt="github")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run memory system benchmarks.")
    parser.add_argument("--live", action="store_true", help="Use real LLM (requires OPENAI_API_KEY).")
    parser.add_argument("--offline", action="store_true", help="Force deterministic offline mode.")
    args = parser.parse_args()

    config = load_config(Path(__file__).resolve().parent.parent)
    use_live = args.live or (not args.offline and bool(config.model.api_key))

    if use_live and not config.model.api_key:
        raise SystemExit("Live benchmark requires OPENAI_API_KEY in .env or environment.")

    mode_label = "LIVE" if use_live else "OFFLINE"
    print(f"# Benchmark mode: {mode_label} ({config.model.model_name})\n")

    standard_path = config.data_dir / "conversations.json"
    stress_path = config.data_dir / "advanced_long_context.json"

    standard_conversations = load_conversations(standard_path)
    stress_conversations = load_conversations(stress_path)

    baseline = BaselineAgent(config=config, force_offline=not use_live)
    advanced = AdvancedAgent(config=config, force_offline=not use_live)

    print("# Standard Benchmark\n")
    standard_rows = [
        run_agent_benchmark("Baseline", baseline, standard_conversations, config),
        run_agent_benchmark("Advanced", advanced, standard_conversations, config),
    ]
    print(format_rows(standard_rows))

    baseline_stress = BaselineAgent(config=config, force_offline=not use_live)
    advanced_stress = AdvancedAgent(config=config, force_offline=not use_live)

    print("\n# Long-Context Stress Benchmark\n")
    stress_rows = [
        run_agent_benchmark("Baseline", baseline_stress, stress_conversations, config),
        run_agent_benchmark("Advanced", advanced_stress, stress_conversations, config),
    ]
    print(format_rows(stress_rows))


if __name__ == "__main__":
    main()
