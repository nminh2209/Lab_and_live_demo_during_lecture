"""Mock LLM for offline development and testing."""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock AI agent response. Set OPENAI_API_KEY to use OpenAI.",
        "Agent is running. In production this would be an OpenAI response.",
        "Your question was received by the deployed cloud agent (mock mode).",
    ],
    "docker": ["A container packages your app so it runs the same everywhere."],
    "deploy": ["Deployment moves code from your machine to a server others can reach."],
    "health": ["All systems operational."],
}


def ask(question: str, history: list[dict] | None = None, delay: float = 0.05) -> str:
    time.sleep(delay + random.uniform(0, 0.03))

    question_lower = question.lower()
    if history:
        last_user = next(
            (m["content"] for m in reversed(history) if m["role"] == "user"),
            None,
        )
        recall_phrases = (
            "what did i",
            "what i just",
            "repeat",
            "previous",
            "last message",
            "vừa nói",
            "vừa hỏi",
        )
        if last_user and any(p in question_lower for p in recall_phrases):
            return f'You previously said: "{last_user}"'

    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)

    return random.choice(MOCK_RESPONSES["default"])
