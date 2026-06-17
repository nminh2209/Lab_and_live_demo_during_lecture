import asyncio
import json
import os
import time
from typing import Dict, List, Tuple

import streamlit as st
from dotenv import load_dotenv

from agent.main_agent import MainAgent
from engine.real_llm_judge import RealLLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


class ExpertEvaluator:
    def __init__(self):
        self.retrieval_eval = RetrievalEvaluator()

    def _lexical_similarity(self, answer: str, expected_answer: str) -> float:
        ans = set(answer.lower().replace(".", "").split())
        exp = set(expected_answer.lower().replace(".", "").split())
        if not exp:
            return 0.0
        return len(ans.intersection(exp)) / len(exp)

    async def score(self, case, resp):
        hit_rate = self.retrieval_eval.calculate_hit_rate(
            case.get("expected_retrieval_ids", []), resp.get("retrieved_ids", []), top_k=3
        )
        mrr = self.retrieval_eval.calculate_mrr(
            case.get("expected_retrieval_ids", []), resp.get("retrieved_ids", [])
        )
        lexical = self._lexical_similarity(resp.get("answer", ""), case.get("expected_answer", ""))
        return {
            "faithfulness": round(lexical, 3),
            "relevancy": round(min(1.0, lexical + 0.1), 3),
            "retrieval": {"hit_rate": hit_rate, "mrr": mrr},
        }


def load_dataset(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]
    for idx, item in enumerate(dataset):
        item["id"] = idx + 1
    return dataset


async def run_one_version(
    dataset: List[Dict], version_name: str, api_key: str, judge_model_a: str, judge_model_b: str
) -> Tuple[List[Dict], Dict]:
    judge = RealLLMJudge(api_key=api_key, model_a=judge_model_a, model_b=judge_model_b)
    runner = BenchmarkRunner(
        MainAgent("v2" if "V2" in version_name else "v1"),
        ExpertEvaluator(),
        judge,
    )

    start = time.perf_counter()
    results = await runner.run_all(dataset, batch_size=4)
    runtime = time.perf_counter() - start

    total = len(results)
    avg_score = sum(r["judge"]["final_score"] for r in results) / max(total, 1)
    hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / max(total, 1)
    mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / max(total, 1)
    agreement_rate = sum(r["judge"]["agreement_rate"] for r in results) / max(total, 1)
    avg_latency = sum(r["latency"] for r in results) / max(total, 1)

    app_tokens = sum(r.get("tokens_used", 0) for r in results)
    judge_prompt_tokens = sum(r["judge"].get("tokens_prompt", 0) for r in results)
    judge_completion_tokens = sum(r["judge"].get("tokens_completion", 0) for r in results)
    total_tokens = app_tokens + judge_prompt_tokens + judge_completion_tokens
    est_cost = round((total_tokens / 1000) * 0.0003, 6)

    summary = {
        "metadata": {
            "version": version_name,
            "total": total,
            "runtime_seconds": round(runtime, 3),
            "pass_count": sum(1 for r in results if r["status"] == "pass"),
        },
        "metrics": {
            "avg_score": round(avg_score, 4),
            "hit_rate": round(hit_rate, 4),
            "mrr": round(mrr, 4),
            "agreement_rate": round(agreement_rate, 4),
            "avg_latency_seconds": round(avg_latency, 4),
            "tokens_total": total_tokens,
            "cost_usd_total": est_cost,
            "cost_usd_per_case": round(est_cost / max(total, 1), 6),
        },
    }
    return results, summary


def release_gate(v1_summary: Dict, v2_summary: Dict) -> Dict:
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    latency_delta = v2_summary["metrics"]["avg_latency_seconds"] - v1_summary["metrics"]["avg_latency_seconds"]
    cost_delta = v2_summary["metrics"]["cost_usd_per_case"] - v1_summary["metrics"]["cost_usd_per_case"]
    thresholds = {
        "quality_delta_min": 0.1,
        "max_latency_seconds": 1.0,
        "max_cost_delta_usd_per_case": 0.00002,
    }
    checks = {
        "quality_ok": delta >= thresholds["quality_delta_min"],
        "latency_ok": v2_summary["metrics"]["avg_latency_seconds"] <= thresholds["max_latency_seconds"],
        "cost_ok": cost_delta <= thresholds["max_cost_delta_usd_per_case"],
    }
    decision = "APPROVE" if all(checks.values()) else "BLOCK_RELEASE"
    return {
        "avg_score_delta": round(delta, 4),
        "latency_delta_seconds": round(latency_delta, 4),
        "cost_delta_usd_per_case": round(cost_delta, 6),
        "thresholds": thresholds,
        "checks": checks,
        "decision": decision,
    }


def main():
    load_dotenv()
    st.set_page_config(page_title="AI Eval Benchmark (Real LLM)", layout="wide")
    st.title("AI Evaluation Benchmarking - Real GPT-4o-mini Demo")
    st.caption("Runs retrieval metrics + real LLM judge + regression gate.")

    dataset_path = st.text_input("Dataset path", "data/golden_set.jsonl")
    max_cases = st.slider("Cases to run (to control API cost)", min_value=5, max_value=60, value=20, step=5)
    judge_model_a = st.text_input("Judge model A", "gpt-4o-mini")
    judge_model_b = st.text_input("Judge model B", "gpt-4o")

    env_key = os.getenv("OPENAI_API_KEY", "")
    user_key = st.text_input(
        "OpenAI API Key (optional if OPENAI_API_KEY exists in .env)",
        value="",
        type="password",
    )
    api_key = user_key.strip() or env_key

    if st.button("Run Real LLM Benchmark", type="primary"):
        if not api_key:
            st.error("Missing API key. Set OPENAI_API_KEY in .env or paste key above.")
            return
        if not os.path.exists(dataset_path):
            st.error(f"Dataset not found: {dataset_path}")
            return

        dataset = load_dataset(dataset_path)[:max_cases]
        with st.spinner("Running V1 and V2 with real GPT-4o-mini judges..."):
            v1_results, v1_summary = asyncio.run(
                run_one_version(dataset, "Agent_V1_RealJudge", api_key, judge_model_a, judge_model_b)
            )
            v2_results, v2_summary = asyncio.run(
                run_one_version(dataset, "Agent_V2_RealJudge", api_key, judge_model_a, judge_model_b)
            )
            gate = release_gate(v1_summary, v2_summary)

        os.makedirs("reports", exist_ok=True)
        payload = {
            "current": v2_summary,
            "regression": {
                "baseline": v1_summary["metadata"]["version"],
                "candidate": v2_summary["metadata"]["version"],
                "avg_score_delta": gate["avg_score_delta"],
                "latency_delta_seconds": gate["latency_delta_seconds"],
                "cost_delta_usd_per_case": gate["cost_delta_usd_per_case"],
                "decision": gate["decision"],
                "gate_thresholds": gate["thresholds"],
                "checks": gate["checks"],
            },
        }
        with open("reports/summary_real_llm.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        with open("reports/benchmark_results_real_llm.json", "w", encoding="utf-8") as f:
            json.dump(v2_results, f, indent=2, ensure_ascii=False)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("V2 Avg Score", v2_summary["metrics"]["avg_score"])
        c2.metric("V2 Hit Rate", v2_summary["metrics"]["hit_rate"])
        c3.metric("V2 MRR", v2_summary["metrics"]["mrr"])
        c4.metric("Decision", gate["decision"], f"Delta score {gate['avg_score_delta']:+}")

        st.subheader("Regression Gate")
        st.json(gate)

        st.subheader("V2 Summary")
        st.json(v2_summary)

        st.subheader("Sample Results (first 5)")
        st.json(v2_results[:5])

        st.success("Done. Saved reports/summary_real_llm.json and reports/benchmark_results_real_llm.json")


if __name__ == "__main__":
    main()
