"""TravelBuddy demo UI — interactive tool-calling travel agent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(ROOT_DIR / ".env")

from agent.graph import run_agent  # noqa: E402
from core.schemas import AgentResult, ToolCallRecord  # noqa: E402

CASES_PATH = ROOT_DIR / "data" / "graded_cases.json"
CATEGORY_LABELS = {
    "normal": ("Chuyến đi", "#22c55e"),
    "edge": ("Ngân sách", "#f59e0b"),
    "clarification": ("Làm rõ", "#38bdf8"),
    "guardrail": ("An toàn", "#ef4444"),
}

INJECT_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"] {
    font-family: "Be Vietnam Pro", "Segoe UI", system-ui, sans-serif !important;
  }
  .block-container { padding-top: 1.25rem; max-width: 1100px; }
  #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
  .tb-hero {
    background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 45%, #0ea5e9 100%);
    border-radius: 16px;
    padding: 1.35rem 1.5rem;
    margin-bottom: 1.25rem;
    color: #f8fafc;
    box-shadow: 0 8px 32px rgba(14, 165, 233, 0.25);
  }
  .tb-hero h1 { margin: 0; font-size: 1.65rem; font-weight: 700; letter-spacing: -0.02em; }
  .tb-hero p { margin: 0.35rem 0 0; opacity: 0.92; font-size: 0.95rem; }
  .tb-stat {
    background: #151f32;
    border: 1px solid #2a3a55;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    min-height: 4.5rem;
  }
  .tb-stat-label {
    color: #94a3b8;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.25rem;
  }
  .tb-stat-value {
    color: #f1f5f9;
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.35;
    word-break: break-word;
  }
  .tb-user {
    background: #1e3a5f;
    border-left: 4px solid #38bdf8;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin: 0.5rem 0;
    color: #f1f5f9;
    line-height: 1.55;
  }
  .tb-assistant {
    background: #14201c;
    border-left: 4px solid #22c55e;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin: 0.5rem 0;
    color: #ecfdf5;
    line-height: 1.6;
    white-space: pre-wrap;
  }
  .tb-tool-card {
    background: #111827;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
  }
  .tb-tool-name {
    color: #38bdf8;
    font-weight: 600;
    font-size: 0.9rem;
  }
  .tb-badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-right: 0.35rem;
  }
  div[data-testid="stTextArea"] textarea {
    font-family: "Be Vietnam Pro", "Segoe UI", sans-serif !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
  }
  div[data-testid="stMetric"] {
    background: transparent !important;
  }
</style>
"""


def fold_vietnamese(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.lower().replace("đ", "d").replace("Đ", "d")


@st.cache_data
def load_sample_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def keyword_in_text(keyword: str, text: str) -> bool:
    return fold_vietnamese(keyword) in fold_vietnamese(text)


def check_keywords(answer: str, case: dict | None) -> dict | None:
    if not case:
        return None
    expected = case.get("expected", {})
    required = expected.get("required_keywords", [])
    forbidden = expected.get("forbidden_keywords", [])
    required_tools = expected.get("required_tools", [])
    return {
        "required_hits": [k for k in required if keyword_in_text(k, answer)],
        "required_missing": [k for k in required if not keyword_in_text(k, answer)],
        "forbidden_hits": [k for k in forbidden if keyword_in_text(k, answer)],
        "required_tools": required_tools,
    }


def render_stat(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="tb-stat">
          <div class="tb-stat-label">{label}</div>
          <div class="tb-stat-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_trace(tool_calls: list[ToolCallRecord]) -> None:
    if not tool_calls:
        st.markdown(
            '<p style="color:#94a3b8;margin:0;">Không có tool call — làm rõ thông tin, từ chối guardrail, hoặc ngoài phạm vi dữ liệu.</p>',
            unsafe_allow_html=True,
        )
        return
    for index, call in enumerate(tool_calls, start=1):
        with st.expander(f"🔧 {index}. {call.name}", expanded=index == 1):
            st.caption("Tham số")
            st.json(call.args, expanded=False)
            st.caption("Kết quả")
            try:
                st.json(json.loads(call.output), expanded=True)
            except json.JSONDecodeError:
                st.code(call.output, language="json")


def run_full_grader(provider: str, today: str) -> dict | None:
    cmd = [
        sys.executable,
        str(ROOT_DIR / "grade" / "scoring.py"),
        "--module",
        "agent.graph",
        "--provider",
        provider,
        "--today",
        today,
    ]
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        st.error("Grader chạy quá 10 phút.")
        return None
    if completed.returncode not in (0, 1) and not completed.stdout.strip():
        st.error(completed.stderr or "Grader thất bại.")
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        st.code(completed.stdout or completed.stderr)
        return None


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "compare_sample" not in st.session_state:
        st.session_state.compare_sample = False
    if "active_case_id" not in st.session_state:
        st.session_state.active_case_id = None


def main() -> None:
    st.set_page_config(
        page_title="TravelBuddy",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(INJECT_CSS, unsafe_allow_html=True)
    init_session()

    cases = load_sample_cases()
    case_by_id = {c["id"]: c for c in cases}

    with st.sidebar:
        st.markdown("### ⚙️ Cài đặt")
        provider_options = ["openai", "google", "ollama"]
        default_provider = os.getenv("TRAVEL_AGENT_PROVIDER", "openai")
        provider = st.selectbox(
            "LLM provider",
            provider_options,
            index=provider_options.index(default_provider)
            if default_provider in provider_options
            else 0,
            label_visibility="collapsed",
        )
        st.caption("Provider")
        today = st.text_input("Ngày tham chiếu", value="2026-05-31")
        st.session_state.compare_sample = st.toggle(
            "So sánh với case mẫu (lab grader)",
            value=st.session_state.compare_sample,
        )
        st.divider()
        st.markdown("**Kịch bản demo**")
        for case in cases:
            cat_label, _ = CATEGORY_LABELS.get(case["category"], (case["category"], "#64748b"))
            if st.button(
                f"{cat_label} · {case['id']}",
                key=f"case_{case['id']}",
                use_container_width=True,
                help=case["query"],
            ):
                st.session_state["query_input"] = case["query"]
                st.session_state.active_case_id = case["id"]
                st.session_state.compare_sample = True
                st.rerun()
        st.divider()
        run_grader_btn = st.button("Chạy grader (6 cases)", use_container_width=True)

    st.markdown(
        """
        <div class="tb-hero">
          <h1>✈️ TravelBuddy</h1>
          <p>Trợ lý du lịch · Tool-calling: chuyến bay → ngân sách → khách sạn · Tiếng Việt</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_chat, tab_grader = st.tabs(["💬 Trò chuyện", "📊 Grader"])

    with tab_chat:
        col_input, col_side = st.columns([3, 1], gap="large")

        with col_input:
            if "query_input" not in st.session_state:
                st.session_state["query_input"] = cases[0]["query"]

            query = st.text_area(
                "Tin nhắn",
                height=100,
                key="query_input",
                placeholder="Ví dụ: Tôi muốn đi Đà Nẵng cuối tuần này từ TP.HCM, budget 5 triệu cho 2 đêm...",
                label_visibility="collapsed",
            )

            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
            with btn_col1:
                submit = st.button("Gửi", type="primary", use_container_width=True)
            with btn_col2:
                if st.button("Xóa", use_container_width=True):
                    st.session_state.messages = []
                    st.session_state.last_result = None
                    st.session_state.active_case_id = None
                    st.rerun()

            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="tb-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="tb-assistant">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

            if submit and query.strip():
                user_text = query.strip()
                st.session_state.messages.append({"role": "user", "content": user_text})
                with st.spinner("Đang xử lý..."):
                    try:
                        result = run_agent(user_text, provider=provider, today=today)
                        st.session_state.last_result = result.model_dump()
                        st.session_state.messages.append(
                            {"role": "assistant", "content": result.final_answer}
                        )
                        matched = next((c for c in cases if c["query"] == user_text), None)
                        if matched:
                            st.session_state.active_case_id = matched["id"]
                    except Exception as exc:
                        st.error(f"Lỗi: {exc}")
                        st.stop()
                st.rerun()

        with col_side:
            st.markdown("**Phạm vi hệ thống**")
            st.caption(
                "Chỉ có chuyến bay nội địa từ TP.HCM trong dataset. "
                "Câu hỏi khác (Tokyo, …) sẽ được giải thích hoặc làm rõ — không phải guardrail."
            )
            if st.session_state.last_result:
                result = AgentResult(**st.session_state.last_result)
                chain = " → ".join(t.name for t in result.tool_calls) or "—"
                render_stat("Provider", result.provider)
                render_stat("Số tool", str(len(result.tool_calls)))
                render_stat("Chuỗi tool", chain)

        if st.session_state.last_result:
            result = AgentResult(**st.session_state.last_result)
            st.markdown("---")
            st.markdown("#### 🔧 Tool trace")
            render_tool_trace(result.tool_calls)

            if st.session_state.compare_sample and st.session_state.active_case_id:
                active_case = case_by_id.get(st.session_state.active_case_id)
                kw = check_keywords(result.final_answer, active_case)
                if kw:
                    st.markdown("#### 📋 So với case lab")
                    if kw["required_hits"]:
                        st.success("✓ Từ khóa: " + ", ".join(kw["required_hits"]))
                    if kw["required_missing"]:
                        st.warning("✗ Thiếu: " + ", ".join(kw["required_missing"]))
                    if kw["forbidden_hits"]:
                        st.error("✗ Từ cấm: " + ", ".join(kw["forbidden_hits"]))
                    expected_tools = kw["required_tools"]
                    actual_tools = [t.name for t in result.tool_calls]
                    if expected_tools:
                        missing = [t for t in expected_tools if t not in actual_tools]
                        if missing:
                            st.warning("✗ Tool thiếu: " + ", ".join(missing))
                        else:
                            st.success("✓ Đủ tools: " + " → ".join(actual_tools))

    with tab_grader:
        st.info("Chạy 6 test cases từ lab (vài phút, tốn API).")
        if run_grader_btn:
            with st.spinner("Đang chấm..."):
                summary = run_full_grader(provider, today)
            if summary:
                st.session_state["grader_summary"] = summary
        if "grader_summary" in st.session_state:
            summary = st.session_state["grader_summary"]
            score = summary["overall_score"]
            color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 65 else "#ef4444"
            st.markdown(
                f'<div class="tb-stat"><div class="tb-stat-label">Overall</div>'
                f'<div class="tb-stat-value" style="color:{color};font-size:1.8rem;">{score}%</div></div>',
                unsafe_allow_html=True,
            )
            st.progress(min(score / 100, 1.0))
            for item in summary["cases"]:
                pct = item["score"] / item["max_score"] if item["max_score"] else 0
                icon = "✅" if pct >= 0.8 else "⚠️"
                with st.expander(f"{icon} {item['case_id']} — {item['score']}/{item['max_score']}", expanded=pct < 0.8):
                    for line in item.get("feedback") or ["Đạt đủ tiêu chí."]:
                        st.write(line)


if __name__ == "__main__":
    main()
