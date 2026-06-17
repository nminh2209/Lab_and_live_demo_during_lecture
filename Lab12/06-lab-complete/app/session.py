"""Conversation history stored in Redis for stateless agents."""
import json
from datetime import datetime, timezone

from app.config import settings
from app.redis_client import get_redis, redis_available

_memory_histories: dict[str, list] = {}


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def get_history(user_id: str) -> list[dict]:
    client = get_redis()
    if redis_available() and client is not None:
        raw = client.get(_history_key(user_id))
        if raw:
            return json.loads(raw)
        return []

    return list(_memory_histories.get(user_id, []))


def append_message(user_id: str, role: str, content: str) -> list[dict]:
    history = get_history(user_id)
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(history) > settings.history_max_messages:
        history = history[-settings.history_max_messages :]

    client = get_redis()
    if redis_available() and client is not None:
        client.setex(
            _history_key(user_id),
            60 * 60 * 24,
            json.dumps(history),
        )
    else:
        _memory_histories[user_id] = history
    return history


def clear_history(user_id: str) -> None:
    client = get_redis()
    if redis_available() and client is not None:
        client.delete(_history_key(user_id))
    else:
        _memory_histories.pop(user_id, None)
