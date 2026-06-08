"""
Compare team chunking strategies on the same 5 benchmark queries.

Requires OPENAI_API_KEY in .env (uses text-embedding-3-small).

    python scripts/compare_strategies.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.bootstrap import build_rag_system
from src.team_strategies import TEAM_STRATEGIES

TEAM_KEYS = ["minh", "duy", "nam", "dung"]
BASELINE_KEYS = ["baseline_fixed", "baseline_sentence"]
ALL_KEYS = TEAM_KEYS + BASELINE_KEYS


def _default_filters() -> dict[str, dict | None]:
    return {key: None for key in ALL_KEYS}


BENCHMARKS = [
    {
        "id": 1,
        "query": "What is Python used for?",
        "gold_source": "python_intro.txt",
        "filters": _default_filters(),
    },
    {
        "id": 2,
        "query": "How does a vector store work?",
        "gold_source": "vector_store_notes.md",
        "filters": {
            **_default_filters(),
            "duy": {"department": "engineering"},
            "nam": {"category": "technical"},
        },
    },
    {
        "id": 3,
        "query": "What is the RAG system architecture?",
        "gold_source": "rag_system_design.md",
        "filters": {
            **_default_filters(),
            "duy": {"department": "engineering"},
            "nam": {"category": "technical"},
        },
    },
    {
        "id": 4,
        "query": "What are common customer support issues?",
        "gold_source": "customer_support_playbook.txt",
        "filters": {
            **_default_filters(),
            "duy": {"department": "support"},
        },
    },
    {
        "id": 5,
        "query": "What are common retrieval failure cases in Vietnamese?",
        "gold_source": "vi_retrieval_notes.md",
        "filters": {key: {"language": "vi"} for key in ALL_KEYS},
    },
]


def source_name(metadata: dict) -> str:
    return Path(metadata.get("source", "unknown")).name


def is_relevant(result: dict, gold_source: str) -> bool:
    return gold_source in source_name(result.get("metadata", {}))


def search(store, query: str, metadata_filter: dict | None, top_k: int = 3) -> list[dict]:
    if metadata_filter:
        return store.search_with_filter(query, top_k=top_k, metadata_filter=metadata_filter)
    return store.search(query, top_k=top_k)


def score_run(store, spec: dict, strategy_key: str) -> dict:
    metadata_filter = spec["filters"].get(strategy_key)
    results = search(store, spec["query"], metadata_filter)
    relevant_count = sum(1 for item in results if is_relevant(item, spec["gold_source"]))
    top1 = results[0] if results else None
    top1_relevant = is_relevant(top1, spec["gold_source"]) if top1 else False
    return {
        "filter": metadata_filter,
        "top1_source": source_name(top1["metadata"]) if top1 else "none",
        "top1_score": top1["score"] if top1 else 0.0,
        "top1_relevant": top1_relevant,
        "relevant_in_top3": relevant_count,
        "rubric_pts": 2 if relevant_count >= 1 and top1_relevant else (1 if relevant_count >= 1 else 0),
        "top3": [f"{source_name(item['metadata'])} ({item['score']:.3f})" for item in results],
    }


def main() -> None:
    stores = {}
    totals = {key: 0 for key in ALL_KEYS}
    chunk_counts = {}
    all_results: dict = {}

    print("=== CHUNKING STRATEGY COMPARISON (OpenAI embeddings) ===\n")
    print("Team: Minh, Duy, Nam, Dũng + 2 baselines (fixed-size, sentence)\n")

    for key in ALL_KEYS:
        info = TEAM_STRATEGIES[key]
        print(f"Building store: {info['member']} — {info['label']} ...")
        store, _ = build_rag_system(
            collection_name=f"compare_{key}",
            llm_provider="mock",
            strategy_key=key,
            require_openai=True,
        )
        stores[key] = store
        chunk_counts[key] = store.get_collection_size()
        print(f"  {key.upper()}_CHUNKS={chunk_counts[key]}")

    for spec in BENCHMARKS:
        print(f"\nQ{spec['id']}: {spec['query']}")
        all_results[f"q{spec['id']}"] = {}
        for key in ALL_KEYS:
            info = TEAM_STRATEGIES[key]
            result = score_run(stores[key], spec, key)
            totals[key] += result["rubric_pts"]
            all_results[f"q{spec['id']}"][key] = result
            print(
                f"  {info['member']:8s} ({info['label'][:28]:28s}) "
                f"filter={result['filter']} top1={result['top1_source']} "
                f"score={result['top1_score']:.3f} rel_top3={result['relevant_in_top3']}/3 "
                f"rubric={result['rubric_pts']}/2"
            )
            print(f"       top3={result['top3']}")

    print("\n=== RETRIEVAL RUBRIC TOTALS (out of 10) ===")
    print("--- Team strategies ---")
    for key in TEAM_KEYS:
        info = TEAM_STRATEGIES[key]
        print(f"{info['member']:4s} ({info['label']}): {totals[key]}/10  chunks={chunk_counts[key]}")
    print("--- Baselines ---")
    for key in BASELINE_KEYS:
        info = TEAM_STRATEGIES[key]
        print(f"{info['member']:4s} ({info['label']}): {totals[key]}/10  chunks={chunk_counts[key]}")

    summary_path = ROOT / "report" / "compare_results.json"
    summary_path.write_text(
        json.dumps(
            {
                "chunk_counts": chunk_counts,
                "totals": totals,
                "benchmarks": all_results,
                "strategies": {k: TEAM_STRATEGIES[k]["label"] for k in ALL_KEYS},
                "team_keys": TEAM_KEYS,
                "baseline_keys": BASELINE_KEYS,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved: {summary_path}")


if __name__ == "__main__":
    main()
