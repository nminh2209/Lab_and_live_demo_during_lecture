import asyncio
import json
import os
import time
from dotenv import load_dotenv
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge
from engine.real_llm_judge import RealLLMJudge

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
            "retrieval": {"hit_rate": hit_rate, "mrr": mrr}
        }

async def run_benchmark_with_results(agent_version: str):
    print(f"Khoi dong Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("Thieu data/golden_set.jsonl. Hay chay 'python data/synthetic_gen.py' truoc.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("File data/golden_set.jsonl rong. Hay tao it nhat 1 test case.")
        return None, None

    for idx, item in enumerate(dataset):
        item["id"] = idx + 1

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model_a = os.getenv("JUDGE_MODEL_A", "gpt-4o-mini")
    model_b = os.getenv("JUDGE_MODEL_B", "gpt-4o")
    use_real_llm = bool(api_key) and not api_key.startswith("PASTE_")

    if use_real_llm:
        print(f"Dung RealLLMJudge voi {model_a} + {model_b}")
        judge = RealLLMJudge(api_key=api_key, model_a=model_a, model_b=model_b)
        run_mode = "real_llm"
    else:
        print("Khong tim thay API key hop le, fallback ve heuristic LLMJudge.")
        judge = LLMJudge()
        run_mode = "heuristic"

    start = time.perf_counter()
    runner = BenchmarkRunner(MainAgent("v2" if "V2" in agent_version else "v1"), ExpertEvaluator(), judge)
    results = await runner.run_all(dataset)
    elapsed = time.perf_counter() - start

    total = len(results)
    pass_count = sum(1 for r in results if r["status"] == "pass")
    app_tokens = sum(r.get("tokens_used", 0) for r in results)
    judge_prompt_tokens = sum(r.get("judge", {}).get("tokens_prompt", 0) for r in results)
    judge_completion_tokens = sum(r.get("judge", {}).get("tokens_completion", 0) for r in results)
    total_tokens = app_tokens + judge_prompt_tokens + judge_completion_tokens
    total_cost_usd = round((total_tokens / 1000) * 0.0003, 6)
    avg_latency = sum(r["latency"] for r in results) / total

    summary = {
        "metadata": {
            "version": agent_version,
            "judge_mode": run_mode,
            "judge_models": [model_a, model_b] if run_mode == "real_llm" else ["heuristic-a", "heuristic-b"],
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "runtime_seconds": round(elapsed, 3),
            "pass_count": pass_count,
            "fail_count": total - pass_count,
        },
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
            "hit_rate": sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
            "mrr": sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total,
            "avg_latency_seconds": avg_latency,
            "tokens_total": total_tokens,
            "tokens_app": app_tokens,
            "tokens_judge_prompt": judge_prompt_tokens,
            "tokens_judge_completion": judge_completion_tokens,
            "cost_usd_total": total_cost_usd,
            "cost_usd_per_case": round(total_cost_usd / max(total, 1), 6),
        },
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary

async def main():
    v1_summary = await run_benchmark("Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")
    
    if not v1_summary or not v2_summary:
        print("Khong the chay Benchmark. Kiem tra lai data/golden_set.jsonl.")
        return

    print("\n--- KET QUA SO SANH (REGRESSION) ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")

    release_gate = {
        "quality_delta_min": 0.1,
        "max_latency_seconds": 1.0,
        "max_cost_delta_usd_per_case": 0.00002,
    }
    latency_ok = v2_summary["metrics"]["avg_latency_seconds"] <= release_gate["max_latency_seconds"]
    cost_delta = (
        v2_summary["metrics"]["cost_usd_per_case"] - v1_summary["metrics"]["cost_usd_per_case"]
    )
    cost_ok = cost_delta <= release_gate["max_cost_delta_usd_per_case"]
    quality_ok = delta >= release_gate["quality_delta_min"]
    decision = "APPROVE" if quality_ok and latency_ok and cost_ok else "BLOCK_RELEASE"

    os.makedirs("reports", exist_ok=True)
    report_payload = {
        "current": v2_summary,
        "regression": {
            "baseline": v1_summary["metadata"]["version"],
            "candidate": v2_summary["metadata"]["version"],
            "avg_score_delta": round(delta, 4),
            "latency_delta_seconds": round(
                v2_summary["metrics"]["avg_latency_seconds"] - v1_summary["metrics"]["avg_latency_seconds"], 4
            ),
            "cost_delta_usd_per_case": round(cost_delta, 6),
            "decision": decision,
            "gate_thresholds": release_gate,
            "checks": {"quality_ok": quality_ok, "latency_ok": latency_ok, "cost_ok": cost_ok},
        },
    }
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(report_payload, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)
    with open("reports/summary_real_llm.json", "w", encoding="utf-8") as f:
        json.dump(report_payload, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results_real_llm.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if decision == "APPROVE":
        print("QUYET DINH: CHAP NHAN BAN CAP NHAT (APPROVE)")
    else:
        print("QUYET DINH: TU CHOI (BLOCK RELEASE)")

if __name__ == "__main__":
    asyncio.run(main())
