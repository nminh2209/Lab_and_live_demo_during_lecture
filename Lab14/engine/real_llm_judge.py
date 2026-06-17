import asyncio
import json
from typing import Any, Dict

from openai import OpenAI


class RealLLMJudge:
    def __init__(self, api_key: str, model_a: str = "gpt-4o-mini", model_b: str = "gpt-4o"):
        self.model_a = model_a
        self.model_b = model_b
        self.client = OpenAI(api_key=api_key)
        self.personas = {
            "judge_strict": "You are a strict evaluator. Penalize unsupported claims heavily.",
            "judge_balanced": "You are a balanced evaluator. Reward factual coverage and clear tone.",
        }

    def _score_once(self, model: str, persona: str, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        system_prompt = (
            f"{persona}\n"
            "Score answer quality from 1-5. Return JSON with keys: "
            "score (number), reasoning (string), accuracy (1-5), professionalism (1-5), safety (1-5)."
        )
        user_prompt = (
            f"Question:\n{question}\n\n"
            f"Answer:\n{answer}\n\n"
            f"Ground truth:\n{ground_truth}\n"
        )

        response = self.client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        usage = response.usage
        return {
            "score": float(parsed.get("score", 1)),
            "reasoning": parsed.get("reasoning", ""),
            "accuracy": float(parsed.get("accuracy", 1)),
            "professionalism": float(parsed.get("professionalism", 1)),
            "safety": float(parsed.get("safety", 1)),
            "tokens_prompt": getattr(usage, "prompt_tokens", 0) or 0,
            "tokens_completion": getattr(usage, "completion_tokens", 0) or 0,
        }

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        judge_a = await asyncio.to_thread(
            self._score_once,
            self.model_a,
            self.personas["judge_strict"],
            question,
            answer,
            ground_truth,
        )
        judge_b = await asyncio.to_thread(
            self._score_once,
            self.model_b,
            self.personas["judge_balanced"],
            question,
            answer,
            ground_truth,
        )

        score_a = judge_a["score"]
        score_b = judge_b["score"]
        score_gap = abs(score_a - score_b)
        agreement_rate = 1.0 if score_gap == 0 else (0.7 if score_gap <= 1 else 0.4)
        final_score = (score_a + score_b) / 2 if score_gap <= 1 else min(score_a, score_b)

        return {
            "final_score": round(final_score, 3),
            "agreement_rate": agreement_rate,
            "individual_scores": {
                f"{self.model_a}_strict": score_a,
                f"{self.model_b}_balanced": score_b,
            },
            "reasoning": {
                "strict": judge_a["reasoning"],
                "balanced": judge_b["reasoning"],
            },
            "rubric_breakdown": {
                "strict": {
                    "accuracy": judge_a["accuracy"],
                    "professionalism": judge_a["professionalism"],
                    "safety": judge_a["safety"],
                },
                "balanced": {
                    "accuracy": judge_b["accuracy"],
                    "professionalism": judge_b["professionalism"],
                    "safety": judge_b["safety"],
                },
            },
            "score_gap": score_gap,
            "tokens_prompt": judge_a["tokens_prompt"] + judge_b["tokens_prompt"],
            "tokens_completion": judge_a["tokens_completion"] + judge_b["tokens_completion"],
        }
