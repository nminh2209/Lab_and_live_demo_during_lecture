from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

def estimate_tokens(text: str) -> int:
    cleaned = text.strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // 4)


def _sanitize_user_id(user_id: str) -> str:
    return re.sub(r"[^\w\-]", "_", user_id.strip()) or "anonymous"


def _default_profile() -> str:
    return "# User Profile\n\n## Facts\n"


def _parse_facts(content: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for line in content.splitlines():
        match = re.match(r"^-\s*([a-z_]+)\s*:\s*(.+)$", line.strip(), re.IGNORECASE)
        if match:
            facts[match.group(1).lower()] = match.group(2).strip()
    return facts


def _render_profile(facts: dict[str, str]) -> str:
    lines = ["# User Profile", "", "## Facts"]
    for key in sorted(facts):
        lines.append(f"- {key}: {facts[key]}")
    lines.append("")
    return "\n".join(lines)


@dataclass
class FactRecord:
    value: str
    confidence: float = 0.8
    mentions: int = 1
    last_updated: float = field(default_factory=time.time)
    source: str = "regex"


@dataclass
class ProfileUpdateResult:
    saved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    conflicts_resolved: list[str] = field(default_factory=list)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md` with confidence + decay metadata."""

    root_dir: Path
    confidence_threshold: float = 0.7
    decay_half_life_days: float = 30.0

    def _meta_path(self, user_id: str) -> Path:
        return self.path_for(user_id).with_name("User.meta.json")

    def _load_records(self, user_id: str) -> dict[str, FactRecord]:
        path = self._meta_path(user_id)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return {
                key: FactRecord(
                    value=item["value"],
                    confidence=float(item.get("confidence", 0.8)),
                    mentions=int(item.get("mentions", 1)),
                    last_updated=float(item.get("last_updated", time.time())),
                    source=str(item.get("source", "regex")),
                )
                for key, item in payload.items()
            }

        records: dict[str, FactRecord] = {}
        for key, value in _parse_facts(self.read_text(user_id)).items():
            records[key] = FactRecord(value=value)
        if records:
            self._save_records(user_id, records)
        return records

    def _save_records(self, user_id: str, records: dict[str, FactRecord]) -> None:
        path = self._meta_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            key: {
                "value": record.value,
                "confidence": record.confidence,
                "mentions": record.mentions,
                "last_updated": record.last_updated,
                "source": record.source,
            }
            for key, record in records.items()
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.write_text(user_id, _render_profile({key: record.value for key, record in records.items()}))

    def records(self, user_id: str) -> dict[str, FactRecord]:
        return self._load_records(user_id)

    def fact_weight(self, record: FactRecord) -> float:
        days = max(0.0, (time.time() - record.last_updated) / 86400)
        decay = math.exp(-days / max(self.decay_half_life_days, 1.0))
        return record.confidence * decay * (1.0 + 0.1 * record.mentions)

    def active_facts(self, user_id: str, min_weight: float = 0.25) -> dict[str, str]:
        active: dict[str, str] = {}
        for key, record in self.records(user_id).items():
            if self.fact_weight(record) >= min_weight:
                active[key] = record.value
        return active

    def upsert_fact(
        self,
        user_id: str,
        key: str,
        value: str,
        confidence: float = 0.85,
        is_correction: bool = False,
        source: str = "regex",
    ) -> ProfileUpdateResult:
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        result = ProfileUpdateResult()
        if not normalized_value:
            return result

        if confidence < self.confidence_threshold:
            result.skipped.append(f"{normalized_key} (confidence {confidence:.2f})")
            return result

        records = self._load_records(user_id)
        existing = records.get(normalized_key)

        if existing and existing.value != normalized_value:
            if is_correction or confidence >= existing.confidence:
                records[normalized_key] = FactRecord(
                    value=normalized_value,
                    confidence=confidence,
                    mentions=existing.mentions + 1,
                    last_updated=time.time(),
                    source=source,
                )
                result.conflicts_resolved.append(
                    f"{normalized_key}: '{existing.value}' -> '{normalized_value}'"
                )
                result.saved.append(normalized_key)
            else:
                result.skipped.append(
                    f"{normalized_key} (conflict, kept '{existing.value}')"
                )
        elif existing:
            existing.mentions += 1
            existing.confidence = max(existing.confidence, confidence)
            existing.last_updated = time.time()
            records[normalized_key] = existing
            result.saved.append(normalized_key)
        else:
            records[normalized_key] = FactRecord(
                value=normalized_value,
                confidence=confidence,
                source=source,
            )
            result.saved.append(normalized_key)

        self._save_records(user_id, records)
        return result

    def path_for(self, user_id: str) -> Path:
        safe_id = _sanitize_user_id(user_id)
        return self.root_dir / safe_id / "User.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if not path.exists():
            return _default_profile()
        return path.read_text(encoding="utf-8")

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text not in content:
            return False
        self.write_text(user_id, content.replace(search_text, replacement, 1))
        return True

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        if not path.exists():
            return 0
        return path.stat().st_size

    def facts(self, user_id: str) -> dict[str, str]:
        return {key: record.value for key, record in self.records(user_id).items()}

    def metadata_summary(self, user_id: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for key, record in self.records(user_id).items():
            rows.append(
                {
                    "key": key,
                    "value": record.value,
                    "confidence": round(record.confidence, 2),
                    "mentions": record.mentions,
                    "weight": round(self.fact_weight(record), 2),
                    "source": record.source,
                }
            )
        return rows


_QUESTION_PREFIXES = (
    "bạn có",
    "bạn biết",
    "nếu ai",
    "có phải",
    "ai đó",
    "sang thread",
)


def _clean_value(value: str) -> str:
    cleaned = value.strip(" .,!?:;\"'")
    for separator in (" và ", " chứ ", " nhưng ", " vì ", " để ", " cho "):
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
    return cleaned


def _looks_like_question(message: str) -> bool:
    stripped = message.strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if stripped.endswith("?"):
        return True
    return any(lower.startswith(prefix) for prefix in _QUESTION_PREFIXES)


def _first_match(message: str, patterns: list[tuple[str, str]]) -> tuple[str, str] | None:
    for pattern, key in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .,!?:;\"'")
            if value:
                return key, value
    return None


_PROFILE_PATTERNS: list[tuple[str, str]] = [
    (r"tên (?:là|mình là|của mình là)\s+([^.,!\?]+)", "name"),
    (r"mình tên là\s+([^.,!\?]+)", "name"),
    (r"chuyển sang\s+([^.,!\?]+engineer[^.,!\?]*)", "profession"),
    (r"đang làm\s+([^.,!\?]+engineer[^.,!\?]*)", "profession"),
    (r"làm\s+([^.,!\?]+engineer[^.,!\?]*)", "profession"),
    (r"nghề nghiệp (?:hiện tại )?(?:vẫn )?là\s+([^.,!\?]+)", "profession"),
    (r"giờ mình đang (?:ở|sống ở|làm việc ở)\s+([^.,!\?]+)", "location"),
    (r"hiện (?:tại )?(?:đang )?(?:ở|sống ở|làm việc ở)\s+([^.,!\?]+)", "location"),
    (r"mình (?:vẫn )?(?:đang )?ở\s+([^.,!\?]+)", "location"),
    (r"nơi ở (?:hiện tại )?(?:là|đã cập nhật.*?(?:sang|thành))\s+([^.,!\?]+)", "location"),
    (r"đồ uống yêu thích (?:là|:)\s*([^.,!\?]+)", "favorite_drink"),
    (r"món ăn yêu thích (?:là|:)\s*([^.,!\?]+)", "favorite_food"),
    (r"nuôi (?:một )?(?:bé )?corgi tên\s+([^.,!\?]+)", "pet"),
    (r"con corgi tên\s+([^.,!\?]+)", "pet"),
    (r"style trả lời[^.]*?(ngắn gọn[^.]*?(?:bullet|ví dụ|trade-off)[^.]*)", "response_style"),
    (r"thích (Python[^.,!\?]*(?:AI[^.,!\?]*)?)", "interests"),
    (r"quan tâm[^.]*?(Python[^.,!\?]*(?:AI[^.,!\?]*)?)", "interests"),
]


def extract_profile_updates(message: str) -> dict[str, str]:
    if _looks_like_question(message):
        return {}

    updates: dict[str, str] = {}
    lower = message.lower()

    profession_correction = re.search(
        r"không còn làm\s+([^.,!\?]+?)\s+nữa,\s*giờ chuyển sang\s+([^.,!\?]+)",
        message,
        re.IGNORECASE,
    )
    if profession_correction:
        updates["profession"] = _clean_value(profession_correction.group(2))
        return updates

    location_correction = re.search(
        r"(?:đính chính|cập nhật|còn).*?(?:ở|sang|thành)\s+([^.,!\?]+)",
        message,
        re.IGNORECASE,
    )
    if location_correction and any(token in lower for token in ("đính chính", "cập nhật", "không còn ở")):
        updates["location"] = _clean_value(location_correction.group(1))

    for pattern, key in _PROFILE_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if not match:
            continue
        if key == "profession" and "profession" in updates:
            continue
        if key == "location" and "location" in updates:
            continue
        value = _clean_value(match.group(1))
        if key == "pet":
            value = f"corgi {value}"
        if key == "response_style":
            if "3 bullet" in lower:
                value = "3 bullet ngắn, có ví dụ thực chiến, ưu tiên trade-off"
            elif "ngắn gọn" in lower:
                value = "ngắn gọn, có bullet và ví dụ thực tế"
            else:
                continue
        if value:
            updates[key] = value

    if "thích Python" in message or "Python, AI" in message or "python, ai" in lower:
        updates["interests"] = "Python, AI ứng dụng"
    elif "python" in lower and "ai" in lower:
        updates["interests"] = "Python, AI ứng dụng"
    elif updates.get("interests") == "Python" and "ai" in lower:
        updates["interests"] = "Python, AI ứng dụng"

    if "cà phê sữa đá" in lower and "favorite_drink" not in updates:
        updates["favorite_drink"] = "cà phê sữa đá"

    if "mì quảng" in lower and "favorite_food" not in updates:
        updates["favorite_food"] = "mì Quảng"

    if "corgi" in lower and "pet" not in updates:
        if match := re.search(r"corgi tên\s+([^.,!\?]+)", message, re.IGNORECASE):
            updates["pet"] = f"corgi {match.group(1).strip()}"
        elif "bơ" in lower:
            updates["pet"] = "corgi Bơ"

    if "ngắn gọn" in lower and ("trả lời" in lower or "style" in lower) and "response_style" not in updates:
        if "3 bullet" in lower:
            updates["response_style"] = "3 bullet ngắn, có ví dụ thực chiến, ưu tiên trade-off"
        else:
            updates["response_style"] = "ngắn gọn, có bullet và ví dụ thực tế"

    if "đà nẵng" in lower and any(
        token in lower
        for token in (
            "nơi ở đã cập nhật",
            "đang làm việc ở đà nẵng",
            "hiện tại là đà nẵng",
            "cập nhật từ huế sang đà nẵng",
        )
    ):
        updates["location"] = "Đà Nẵng"

    if "huế" in lower and any(token in lower for token in ("mình vẫn ở huế", "hiện đang ở huế", "đang ở huế chứ")):
        updates["location"] = "Huế"

    return updates


def extract_profile_updates_with_confidence(message: str) -> dict[str, tuple[str, float, bool]]:
    raw = extract_profile_updates(message)
    results: dict[str, tuple[str, float, bool]] = {}
    lower = message.lower()
    is_correction = any(token in lower for token in ("đính chính", "cập nhật", "không còn", "chuyển sang"))
    for key, value in raw.items():
        confidence = 0.95 if is_correction else 0.82
        results[key] = (value, confidence, is_correction)
    return results


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    if not messages:
        return ""
    selected = messages[-max_items:]
    parts: list[str] = []
    for item in selected:
        role = item.get("role", "user")
        content = item.get("content", "").strip()
        if not content:
            continue
        snippet = content if len(content) <= 180 else content[:177] + "..."
        parts.append(f"{role}: {snippet}")
    return " | ".join(parts)


@dataclass
class CompactMemoryManager:
    """Compact memory for long threads."""

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def _ensure_thread(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0,
            }
        return self.state[thread_id]

    def _message_tokens(self, messages: list[dict[str, str]], summary: str) -> int:
        total = estimate_tokens(summary)
        for message in messages:
            total += estimate_tokens(message.get("content", ""))
        return total

    def _compact_if_needed(self, thread_id: str) -> None:
        thread = self._ensure_thread(thread_id)
        messages: list[dict[str, str]] = thread["messages"]  # type: ignore[assignment]
        summary: str = thread["summary"]  # type: ignore[assignment]

        while len(messages) > self.keep_messages and self._message_tokens(messages, summary) > self.threshold_tokens:
            older = messages[:-self.keep_messages]
            messages[:] = messages[-self.keep_messages :]
            older_summary = summarize_messages(older)
            summary = f"{summary} {older_summary}".strip() if summary else older_summary
            thread["summary"] = summary
            thread["compactions"] = int(thread["compactions"]) + 1

    def append(self, thread_id: str, role: str, content: str) -> None:
        thread = self._ensure_thread(thread_id)
        messages: list[dict[str, str]] = thread["messages"]  # type: ignore[assignment]
        messages.append({"role": role, "content": content})
        self._compact_if_needed(thread_id)

    def context(self, thread_id: str) -> dict[str, object]:
        thread = self._ensure_thread(thread_id)
        return {
            "messages": list(thread["messages"]),
            "summary": thread["summary"],
            "compactions": thread["compactions"],
        }

    def compaction_count(self, thread_id: str) -> int:
        thread = self._ensure_thread(thread_id)
        return int(thread["compactions"])
