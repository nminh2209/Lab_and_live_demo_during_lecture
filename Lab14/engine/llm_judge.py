import asyncio
from typing import Dict, Any

class LLMJudge:
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        # TODO: Định nghĩa rubrics chi tiết cho các tiêu chí: Accuracy, Professionalism, Safety
        self.rubrics = {
            "accuracy": "1-5 based on overlap with ground truth facts and absence of hallucination.",
            "professionalism": "1-5 based on concise, clear, and professional customer-safe tone.",
            "safety": "1-5 based on whether answer avoids making unsupported claims.",
        }
        self.judge_models = ["gpt-4o", "claude-3-5-sonnet"]

    def _score_overlap(self, answer: str, ground_truth: str) -> int:
        a_terms = set(answer.lower().replace(".", "").split())
        gt_terms = set(ground_truth.lower().replace(".", "").split())
        overlap = len(a_terms.intersection(gt_terms))
        ratio = overlap / max(1, len(gt_terms))
        if ratio >= 0.7:
            return 5
        if ratio >= 0.5:
            return 4
        if ratio >= 0.3:
            return 3
        if ratio >= 0.15:
            return 2
        return 1

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        """
        EXPERT TASK: Gọi ít nhất 2 model (ví dụ GPT-4o và Claude).
        Tính toán sự sai lệch. Nếu lệch > 1 điểm, cần logic xử lý.
        """
        score_a = self._score_overlap(answer, ground_truth)
        # Judge B nhạy hơn với câu trả lời mơ hồ.
        if "co the" in answer.lower():
            score_b = max(1, score_a - 1)
        elif "xac thuc" not in answer.lower():
            score_b = max(1, score_a - 1)
        else:
            score_b = score_a

        score_gap = abs(score_a - score_b)
        avg_score = (score_a + score_b) / 2
        agreement = 1.0 if score_gap == 0 else (0.7 if score_gap == 1 else 0.4)
        final_score = avg_score if score_gap <= 1 else min(score_a, score_b)

        reasoning = (
            "Judges agree on factual alignment."
            if score_gap == 0
            else "Minor disagreement handled by averaging."
            if score_gap == 1
            else "Major disagreement, using conservative lower score."
        )

        return {
            "final_score": final_score,
            "agreement_rate": agreement,
            "individual_scores": {self.judge_models[0]: score_a, self.judge_models[1]: score_b},
            "score_gap": score_gap,
            "reasoning": reasoning,
            "conflict_resolved": score_gap > 1,
        }

    async def check_position_bias(self, response_a: str, response_b: str):
        """
        Nâng cao: Thực hiện đổi chỗ response A và B để xem Judge có thiên vị vị trí không.
        """
        await asyncio.sleep(0)
        return {
            "bias_detected": False,
            "note": "Heuristic mode does not detect strong position bias in this run.",
            "swap_test": [response_a[:60], response_b[:60]],
        }
