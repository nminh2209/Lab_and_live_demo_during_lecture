"""Streamlit demo for Day 17 Memory Systems lab."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from agent_advanced import AdvancedAgent  # noqa: E402
from agent_baseline import BaselineAgent  # noqa: E402
from benchmark import format_rows, load_conversations, run_agent_benchmark  # noqa: E402
from config import LabConfig, load_config  # noqa: E402
from model_provider import ProviderConfig  # noqa: E402


def build_runtime_config(api_key: str, model_name: str, confidence: float) -> LabConfig:
    base = load_config(ROOT)
    base.model = ProviderConfig(
        provider="openai",
        model_name=model_name,
        temperature=0.2,
        api_key=api_key,
    )
    base.profile_confidence_threshold = confidence
    return base


def init_session() -> None:
    defaults = {
        "messages": [],
        "thread_id": f"thread-{uuid.uuid4().hex[:8]}",
        "user_id": "demo_user",
        "agent_kind": "Advanced",
        "stats": {"prompt": 0, "completion": 0},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_agent(config: LabConfig):
    if st.session_state.agent_kind == "Baseline":
        return BaselineAgent(config=config, force_offline=False)
    return AdvancedAgent(config=config, force_offline=False)


def render_chat(agent) -> None:
    for item in st.session_state.messages:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if meta := item.get("meta"):
                st.caption(meta)

    prompt = st.chat_input("Nhập tin nhắn tiếng Việt...")
    if not prompt:
        return

    result = agent.reply(
        st.session_state.user_id,
        st.session_state.thread_id,
        prompt,
    )

    st.session_state.stats["prompt"] += int(result.get("prompt_tokens") or 0)
    st.session_state.stats["completion"] += int(result.get("agent_tokens") or 0)

    meta = (
        f"mode={result.get('mode')} | model={result.get('model', 'n/a')} | "
        f"prompt={result.get('prompt_tokens', 0)} | completion={result.get('agent_tokens', 0)}"
    )
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "meta": meta}
    )
    st.rerun()


def render_memory_panel(agent) -> None:
    if not isinstance(agent, AdvancedAgent):
        st.info("Baseline agent không dùng User.md.")
        return

    user_id = st.session_state.user_id
    st.subheader("User.md")
    st.code(agent.profile_store.read_text(user_id), language="markdown")

    st.subheader("Fact metadata (confidence + decay weight)")
    st.dataframe(agent.profile_store.metadata_summary(user_id), use_container_width=True)

    st.subheader("Compact memory")
    context = agent.compact_memory.context(st.session_state.thread_id)
    st.write(f"Compactions: **{context.get('compactions', 0)}**")
    st.text_area("Summary", str(context.get("summary", "")), height=120)

    updates = agent.last_profile_update.get(user_id)
    if updates:
        st.subheader("Last profile write decision")
        st.json(updates)


def render_benchmark(config: LabConfig) -> None:
    st.warning("Benchmark live sẽ gọi GPT-4 nhiều lần và tốn token thật.")
    suite = st.selectbox("Dataset", ["Standard (1 conv)", "Standard (full)", "Stress (full)"])
    if st.button("Run live benchmark"):
        conversations = load_conversations(config.data_dir / "conversations.json")
        stress = load_conversations(config.data_dir / "advanced_long_context.json")

        if suite == "Standard (1 conv)":
            selected = conversations[:1]
        elif suite == "Standard (full)":
            selected = conversations
        else:
            selected = stress

        with st.spinner("Running..."):
            baseline = BaselineAgent(config=config, force_offline=False)
            advanced = AdvancedAgent(config=config, force_offline=False)
            rows = [
                run_agent_benchmark("Baseline", baseline, selected, config),
                run_agent_benchmark("Advanced", advanced, selected, config),
            ]
        st.markdown(format_rows(rows))


def main() -> None:
    st.set_page_config(page_title="Memory Systems Demo", layout="wide")
    init_session()

    st.title("Day 17 — Memory Systems for AI Agent")
    st.caption("So sánh Baseline vs Advanced với GPT-4 thật, User.md, compact memory, và bonus guardrails.")

    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("OpenAI API Key", type="password", help="gpt-4o recommended")
        model_name = st.selectbox("Model", ["gpt-4o", "gpt-4-turbo", "gpt-4o-mini"], index=0)
        st.session_state.agent_kind = st.radio("Agent", ["Baseline", "Advanced"])
        st.session_state.user_id = st.text_input("User ID", st.session_state.user_id)
        st.session_state.thread_id = st.text_input("Thread ID", st.session_state.thread_id)
        confidence = st.slider("Profile confidence threshold", 0.5, 0.95, 0.7, 0.05)

        if st.button("New thread"):
            st.session_state.thread_id = f"thread-{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.rerun()

        if st.button("Clear chat"):
            st.session_state.messages = []
            st.rerun()

    if not api_key:
        st.info("Nhập OpenAI API key ở sidebar để bắt đầu demo live.")
        st.markdown(
            """
**Bonus features (90–100 rubric):**
- **Confidence threshold** — chỉ ghi User.md khi fact đủ tin cậy
- **Conflict handling** — đính chính thay fact cũ, không giữ mâu thuẫn
- **Memory decay** — fact cũ giảm trọng số theo thời gian
- **LLM entity extraction** — GPT-4 trích fact có cấu trúc khi chạy live
            """
        )
        return

    config = build_runtime_config(api_key, model_name, confidence)
    agent = get_agent(config)

    col1, col2, col3 = st.columns(3)
    col1.metric("Prompt tokens (session)", st.session_state.stats["prompt"])
    col2.metric("Completion tokens (session)", st.session_state.stats["completion"])
    if isinstance(agent, AdvancedAgent):
        col3.metric("Compactions", agent.compaction_count(st.session_state.thread_id))
    else:
        col3.metric("Compactions", 0)

    tab_chat, tab_memory, tab_bench, tab_about = st.tabs(["Chat", "Memory", "Benchmark", "About"])

    with tab_chat:
        render_chat(agent)

    with tab_memory:
        render_memory_panel(agent)

    with tab_bench:
        render_benchmark(config)

    with tab_about:
        st.markdown(
            """
### Architecture
1. **Baseline** — short-term memory trong cùng thread, không User.md
2. **Advanced** — User.md (persistent) + compact memory (long threads)

### Trade-offs
- Advanced tốn token hơn ở hội thoại ngắn (profile overhead)
- Advanced thắng recall cross-session và prompt cost ở thread dài nhờ compact

### Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
python src/benchmark.py --live
```
            """
        )


if __name__ == "__main__":
    main()
