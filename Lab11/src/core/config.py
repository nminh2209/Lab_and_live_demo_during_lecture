"""
Lab 11 — Configuration & API Key Setup
"""
import os
from pathlib import Path


def _load_dotenv():
    """Load .env from project root if present."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


# OpenAI model used across agents, judges, and red-team generation
LLM_MODEL = "gpt-4o-mini"
LITELLM_MODEL = "openai/gpt-4o-mini"


def get_adk_model():
    """Return the ADK LiteLLM wrapper for the configured OpenAI model."""
    from google.adk.models.lite_llm import LiteLlm
    return LiteLlm(model=LITELLM_MODEL)


def setup_api_key():
    """Load OpenAI API key from .env, environment, or prompt."""
    _load_dotenv()
    if "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"]:
        os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API Key: ")
    print(f"API key loaded. Using model: {LLM_MODEL}")


# Allowed banking topics (used by topic_filter)
ALLOWED_TOPICS = [
    "banking", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit",
    "deposit", "withdrawal", "balance", "payment",
    "tai khoan", "giao dich", "tiet kiem", "lai suat",
    "chuyen tien", "the tin dung", "so du", "vay",
    "ngan hang", "atm",
]

# Blocked topics (immediate reject)
BLOCKED_TOPICS = [
    "hack", "exploit", "weapon", "drug", "illegal",
    "violence", "gambling", "bomb", "kill", "steal",
]
