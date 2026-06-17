"""Monthly cost guard — tracks LLM spend per user in Redis."""
import json
import time
from dataclasses import dataclass

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis, redis_available

PRICE_PER_1K_INPUT = 0.00015
PRICE_PER_1K_OUTPUT = 0.0006

_memory_usage: dict[str, dict] = {}


@dataclass
class UsageSnapshot:
    user_id: str
    month: str
    cost_usd: float
    request_count: int


def _month_key() -> str:
    return time.strftime("%Y-%m")


def _storage_key(user_id: str) -> str:
    return f"cost:{user_id}:{_month_key()}"


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        (input_tokens / 1000) * PRICE_PER_1K_INPUT
        + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT
    )


def _load_usage(user_id: str) -> UsageSnapshot:
    month = _month_key()
    client = get_redis()
    if redis_available() and client is not None:
        raw = client.get(_storage_key(user_id))
        if raw:
            data = json.loads(raw)
            return UsageSnapshot(
                user_id=user_id,
                month=data.get("month", month),
                cost_usd=float(data.get("cost_usd", 0)),
                request_count=int(data.get("request_count", 0)),
            )
        return UsageSnapshot(user_id=user_id, month=month, cost_usd=0.0, request_count=0)

    data = _memory_usage.get(user_id, {})
    if data.get("month") != month:
        return UsageSnapshot(user_id=user_id, month=month, cost_usd=0.0, request_count=0)
    return UsageSnapshot(
        user_id=user_id,
        month=month,
        cost_usd=float(data.get("cost_usd", 0)),
        request_count=int(data.get("request_count", 0)),
    )


def _save_usage(snapshot: UsageSnapshot) -> None:
    payload = {
        "month": snapshot.month,
        "cost_usd": snapshot.cost_usd,
        "request_count": snapshot.request_count,
    }
    client = get_redis()
    if redis_available() and client is not None:
        client.setex(_storage_key(snapshot.user_id), 60 * 60 * 24 * 35, json.dumps(payload))
        return
    _memory_usage[snapshot.user_id] = payload


def check_budget(user_id: str) -> UsageSnapshot:
    usage = _load_usage(user_id)
    if usage.cost_usd >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(usage.cost_usd, 4),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "first day of next month UTC",
            },
        )
    return usage


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> UsageSnapshot:
    usage = _load_usage(user_id)
    usage.cost_usd += _estimate_cost(input_tokens, output_tokens)
    usage.request_count += 1
    _save_usage(usage)
    return usage


def get_usage(user_id: str) -> dict:
    usage = _load_usage(user_id)
    return {
        "user_id": user_id,
        "month": usage.month,
        "requests": usage.request_count,
        "cost_usd": round(usage.cost_usd, 4),
        "budget_usd": settings.monthly_budget_usd,
        "budget_remaining_usd": round(
            max(0, settings.monthly_budget_usd - usage.cost_usd), 4
        ),
    }
