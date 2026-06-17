"""Observability + mitigations for the opaque e-commerce agent."""
from __future__ import annotations

import copy
import re
import threading
import time
import unicodedata

from telemetry.cost import cost_from_usage
from telemetry.logger import logger, set_correlation_id
from telemetry.redact import redact
from telemetry.tracing import Tracer

_PROMPT = ""
try:
    with open("solution/prompt.txt", encoding="utf-8") as f:
        _PROMPT = f.read().strip()
except OSError:
    pass

_ORDER_PREFIX_RE = re.compile(r"(?i)^ORDER:\s*")
_GHI_CHU_BLOCK_RE = re.compile(
    r"(?:\n|\s)*GHI\s*CHU(?:\s*(?:KHACH|KHÁCH))?\s*:.*$",
    re.I | re.DOTALL,
)
_INJECT_PAREN_RE = re.compile(
    r"\([^)]*(?:system|override|tong\s*cong|gia\s*la|price\s*is|he\s*thong)[^)]*\)",
    re.I,
)
_CONTACT_RE = re.compile(
    r"(?i)\b(?:goi minh qua sdt|lien he(?:\s+email)?|contact|email)\b.*$"
)
_QTY_RE = re.compile(r"(?i)\bmua\s+(\d+)\b")
_SHIP_RE = re.compile(r"(?i)\b(?:ship|giao|den|toi|tới|đến)\b")
_COUPON_RE = re.compile(
    r"(?i)\b(?:ma|coupon|dung ma|ap dung ma|voi coupon)\s+([A-Z0-9]+)\b"
)
_CATALOG_RE = re.compile(r"(?i)\b(iphone|ipad|macbook|airpods)\b")
_UNKNOWN_BRAND_RE = re.compile(r"(?i)\b(nokia|sony|samsung|oppo|xiaomi)\b")


def _normalize_question(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _ORDER_PREFIX_RE.sub("", text).strip()
    text = _GHI_CHU_BLOCK_RE.sub("", text).strip()
    text = _INJECT_PAREN_RE.sub("", text).strip()
    text = _CONTACT_RE.sub("", text).strip()
    text, _ = redact(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_qty(question: str) -> int:
    match = _QTY_RE.search(question)
    return max(1, int(match.group(1))) if match else 1


def _needs_shipping(question: str) -> bool:
    return bool(_SHIP_RE.search(question))


def _needs_discount(question: str) -> bool:
    return bool(_COUPON_RE.search(question))


def _discount_called(trace: list[dict]) -> bool:
    return any(step.get("tool") == "get_discount" for step in trace or [])


def _stock_obs(trace: list[dict]) -> dict | None:
    for step in trace or []:
        if step.get("tool") == "check_stock":
            return step.get("observation") or {}
    return None


def _refusal_answer(trace: list[dict], question: str) -> str | None:
    obs = _stock_obs(trace)
    if not obs:
        return None
    item = obs.get("item") or "san pham"
    if not obs.get("found"):
        if _UNKNOWN_BRAND_RE.search(question):
            brand = _UNKNOWN_BRAND_RE.search(question).group(1).lower()
            return f"Khong tim thay {brand} trong danh muc."
        return f"Khong tim thay {item} trong danh muc."
    if not obs.get("in_stock"):
        return f"{item.title()} hien het hang nen khong the dat mua."
    if obs.get("served", obs.get("destination_served", True)) is False:
        return "Dia diem giao hang khong duoc ho tro."
    return None


def _compute_total(trace: list[dict], qty: int, question: str) -> int | None:
    obs = _stock_obs(trace)
    if not obs:
        return None

    if not obs.get("found") or not obs.get("in_stock"):
        return None
    if obs.get("served", obs.get("destination_served", True)) is False:
        return None

    unit_price = int(obs.get("unit_price_vnd") or 0)
    discount_pct = 0
    has_discount = False
    shipping = 0
    discount_called = False
    has_shipping = False

    for step in trace or []:
        step_obs = step.get("observation") or {}
        tool = step.get("tool")
        if tool == "get_discount":
            discount_called = True
            if step_obs.get("valid"):
                has_discount = True
                discount_pct = int(step_obs.get("percent") or step_obs.get("discount_pct") or 0)
        elif tool == "calc_shipping":
            has_shipping = True
            shipping = int(step_obs.get("cost_vnd") or 0)

    if _needs_shipping(question) and not has_shipping:
        return None
    if _needs_discount(question) and not discount_called:
        return None

    subtotal = unit_price * qty
    discounted = subtotal * (100 - discount_pct) // 100 if has_discount else subtotal
    return discounted + (shipping if has_shipping else 0)


def _format_success(total: int) -> str:
    return f"Tong cong: {total} VND"


def _sanitize_answer(answer: str) -> str:
    if not answer:
        return answer
    answer = re.sub(r"\(lien he:\s*[^)]*\)", "", answer, flags=re.I)
    answer = re.sub(r"(?i)(goi minh qua sdt|lien he:?).*", "", answer)
    return redact(answer)[0].strip()


def _trace_complete(trace: list[dict], question: str) -> bool:
    tools = {step.get("tool") for step in trace or []}
    if "check_stock" not in tools:
        return False
    if _needs_shipping(question) and "calc_shipping" not in tools:
        return False
    if _needs_discount(question) and not _discount_called(trace):
        return False
    return True


def _apply_guardrails(result: dict, question: str) -> dict:
    trace = result.get("trace") or []
    refusal = _refusal_answer(trace, question)
    if refusal:
        return {**result, "answer": refusal, "status": "ok"}

    total = _compute_total(trace, _parse_qty(question), question)
    if total is None:
        return result

    return {**result, "answer": _format_success(total), "status": "ok"}


def _cache_key(question: str, config: dict) -> str:
    return f"{question}|{config.get('model', '')}|{config.get('temperature', '')}"


def mitigate(call_next, question, config, context):
    qid = context.get("qid", "?")
    session_id = context.get("session_id", "unknown")
    turn = context.get("turn_index", 0)
    cid = f"{session_id}-{qid}-{turn}"
    set_correlation_id(cid)

    conf = copy.deepcopy(config)
    if _PROMPT:
        conf["system_prompt"] = _PROMPT
    question = _normalize_question(question)

    cache = context.get("cache", {})
    lock: threading.Lock = context.get("cache_lock") or threading.Lock()
    key = _cache_key(question, conf)

    if conf.get("cache", {}).get("enabled"):
        with lock:
            hit = cache.get(key)
        if hit is not None:
            logger.log_event("CACHE_HIT", {"qid": qid, "session_id": session_id})
            return hit

    tracer = Tracer()
    attempts = max(1, int(conf.get("retry", {}).get("max_attempts", 1)))
    backoff = int(conf.get("retry", {}).get("backoff_ms", 0))
    retry_on = conf.get("retry", {}).get("enabled", False)
    last = None

    for attempt in range(1, attempts + 1):
        t0 = time.perf_counter()
        with tracer.start_span(
            "invoke_agent",
            gen_ai_request_model=conf.get("model", ""),
            correlation_id=cid,
            qid=qid,
            session_id=session_id,
            turn=turn,
            attempt=attempt,
        ):
            with tracer.start_span("agent_call"):
                last = call_next(question, conf)

        last = _apply_guardrails(last, question)
        wall_ms = int((time.perf_counter() - t0) * 1000)
        meta = last.get("meta", {}) or {}
        usage = meta.get("usage", {}) or {}
        answer = last.get("answer") or ""
        redacted = _sanitize_answer(answer)
        _, pii_hits = redact(answer)

        logger.log_event("AGENT_CALL", {
            "qid": qid,
            "session_id": session_id,
            "turn": turn,
            "attempt": attempt,
            "status": last.get("status"),
            "steps": last.get("steps"),
            "wall_ms": wall_ms,
            "latency_ms": meta.get("latency_ms"),
            "usage": usage,
            "cost_usd": cost_from_usage(meta.get("model", ""), usage),
            "tools_used": meta.get("tools_used", []),
            "tool_count": len(meta.get("tools_used") or []),
            "pii_in_answer": pii_hits > 0,
        })

        if conf.get("redact_pii") or pii_hits > 0:
            last = {**last, "answer": redacted}

        status = last.get("status")
        trace = last.get("trace") or []
        refusal = _refusal_answer(trace, question)
        complete = _trace_complete(trace, question) and (
            refusal is not None or _compute_total(trace, _parse_qty(question), question) is not None
        )
        false_refusal = (
            refusal
            and _CATALOG_RE.search(question)
            and "khong tim thay san pham" in refusal.lower()
        )
        if status in ("ok", "no_action") and complete and not false_refusal:
            break
        if retry_on and attempt < attempts:
            time.sleep(backoff / 1000.0)

    if conf.get("cache", {}).get("enabled") and last and last.get("status") == "ok":
        with lock:
            cache[key] = last

    return last
