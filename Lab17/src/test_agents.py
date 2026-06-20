from __future__ import annotations

import time
from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import LabConfig
from memory_store import CompactMemoryManager, UserProfileStore
from model_provider import ProviderConfig


def make_config(tmp_path: Path) -> LabConfig:
    root = Path(__file__).resolve().parent.parent
    return LabConfig(
        base_dir=root,
        data_dir=root / "data",
        state_dir=tmp_path / "state",
        compact_threshold_tokens=120,
        compact_keep_messages=3,
        model=ProviderConfig(provider="openai", model_name="gpt-4o-mini", temperature=0.2),
        judge_model=ProviderConfig(provider="openai", model_name="gpt-4o-mini", temperature=0.0),
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    store = UserProfileStore(config.state_dir / "profiles")

    store.write_text("alice", "# User Profile\n\n## Facts\n- name: Alice\n")
    assert "Alice" in store.read_text("alice")
    assert store.file_size("alice") > 0

    store.upsert_fact("alice", "location", "Huế")
    assert "Huế" in store.read_text("alice")

    changed = store.edit_text("alice", "Huế", "Đà Nẵng")
    assert changed is True
    assert "Đà Nẵng" in store.read_text("alice")


def test_compact_trigger(tmp_path: Path) -> None:
    manager = CompactMemoryManager(threshold_tokens=80, keep_messages=2)
    thread_id = "long-thread"
    long_message = "Mình " + ("đang test compact memory " * 20)

    for index in range(8):
        manager.append(thread_id, "user", f"{long_message} #{index}")

    assert manager.compaction_count(thread_id) >= 1
    context = manager.context(thread_id)
    assert len(context["messages"]) <= 2


def test_cross_session_recall(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    baseline = BaselineAgent(config=config, force_offline=True)
    advanced = AdvancedAgent(config=config, force_offline=True)
    user_id = "dungct"

    baseline.reply(user_id, "thread-a", "Mình tên là DũngCT và thích Python.")
    baseline_recall = baseline.reply(user_id, "thread-b", "Mình tên gì?")["answer"]

    advanced.reply(user_id, "thread-a", "Mình tên là DũngCT và thích Python.")
    advanced_recall = advanced.reply(user_id, "thread-b", "Mình tên gì?")["answer"]

    assert "DũngCT" not in baseline_recall
    assert "DũngCT" in advanced_recall


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.compact_threshold_tokens = 150
    config.compact_keep_messages = 3

    baseline = BaselineAgent(config=config, force_offline=True)
    advanced = AdvancedAgent(config=config, force_offline=True)
    thread_id = "stress-thread"
    user_id = "stress-user"
    long_message = "Tin tức dài " + ("về benchmark memory " * 25)

    for index in range(12):
        baseline.reply(user_id, thread_id, f"{long_message} #{index}")
        advanced.reply(user_id, thread_id, f"{long_message} #{index}")

    baseline_prompt = baseline.prompt_token_usage(thread_id)
    advanced_prompt = advanced.prompt_token_usage(thread_id)

    assert advanced.compaction_count(thread_id) >= 1
    assert advanced_prompt < baseline_prompt


def test_confidence_threshold_blocks_low_confidence_writes(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles", confidence_threshold=0.7)

    result = store.upsert_fact("user1", "location", "Hà Nội", confidence=0.45)

    assert "location" not in store.facts("user1")
    assert any("confidence 0.45" in item for item in result.skipped)


def test_conflict_handling_updates_stale_profession(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles", confidence_threshold=0.7)

    store.upsert_fact("user1", "profession", "backend engineer", confidence=0.9)
    result = store.upsert_fact(
        "user1",
        "profession",
        "MLOps engineer",
        confidence=0.95,
        is_correction=True,
    )

    assert store.facts("user1")["profession"] == "MLOps engineer"
    assert len(result.conflicts_resolved) == 1
    assert "backend engineer" not in store.read_text("user1")


def test_memory_decay_excludes_stale_facts_from_active_set(tmp_path: Path) -> None:
    store = UserProfileStore(
        tmp_path / "profiles",
        confidence_threshold=0.5,
        decay_half_life_days=1.0,
    )

    store.upsert_fact("user1", "name", "DũngCT", confidence=0.9)
    records = store.records("user1")
    records["name"].last_updated = time.time() - (60 * 86400)
    store._save_records("user1", records)

    assert store.facts("user1")["name"] == "DũngCT"
    assert "name" not in store.active_facts("user1", min_weight=0.25)
