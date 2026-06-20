"""Compare profile writes with vs without bonus guardrails."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from memory_store import UserProfileStore


def run_scenario(store: UserProfileStore, user_id: str) -> dict[str, object]:
    steps: list[tuple[str, str, float, bool]] = [
        ("name", "DũngCT", 0.92, False),
        ("location", "Đà Nẵng", 0.88, False),
        ("profession", "backend engineer", 0.90, False),
        ("hobby", "crypto trading", 0.35, False),  # low-confidence noise
        ("profession", "MLOps engineer", 0.95, True),  # correction
    ]

    saved = 0
    skipped = 0
    conflicts = 0

    for key, value, confidence, is_correction in steps:
        result = store.upsert_fact(
            user_id,
            key,
            value,
            confidence=confidence,
            is_correction=is_correction,
        )
        saved += len(result.saved)
        skipped += len(result.skipped)
        conflicts += len(result.conflicts_resolved)

    facts = store.facts(user_id)
    return {
        "facts": facts,
        "saved_writes": saved,
        "skipped_writes": skipped,
        "conflicts_resolved": conflicts,
        "fact_count": len(facts),
        "noise_hobby_stored": facts.get("hobby") == "crypto trading",
        "profession": facts.get("profession"),
        "location": facts.get("location"),
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent / "state" / "guardrails_demo"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)

    without = UserProfileStore(
        root / "without",
        confidence_threshold=0.0,
        decay_half_life_days=10_000,
    )
    with_guardrails = UserProfileStore(
        root / "with",
        confidence_threshold=0.7,
        decay_half_life_days=30,
    )

    bare = run_scenario(without, "demo_user")
    guarded = run_scenario(with_guardrails, "demo_user")

    with_guardrails.upsert_fact("decay_user", "interests", "Python, AI", confidence=0.9)
    records = with_guardrails.records("decay_user")
    records["interests"].last_updated = time.time() - (90 * 86400)
    with_guardrails._save_records("decay_user", records)
    decay_active = with_guardrails.active_facts("decay_user")

    print("# Guardrails comparison (controlled micro-scenario)\n")
    print("| Metric | Without guardrails | With guardrails |")
    print("|--------|-------------------:|----------------:|")
    print(f"| Facts persisted | {bare['fact_count']} | {guarded['fact_count']} |")
    print(f"| Skipped writes | {bare['skipped_writes']} | {guarded['skipped_writes']} |")
    print(f"| Conflicts resolved | {bare['conflicts_resolved']} | {guarded['conflicts_resolved']} |")
    print(f"| Low-confidence hobby stored | {bare['noise_hobby_stored']} | {guarded['noise_hobby_stored']} |")
    print(f"| Final profession | {bare['profession']} | {guarded['profession']} |")
    print(f"| Location kept after noise | {bare['location']} | {guarded['location']} |")
    print(f"| Stale fact in active set after 90d | yes | {'interests' in decay_active} |")


if __name__ == "__main__":
    main()
