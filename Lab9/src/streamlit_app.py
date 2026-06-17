from __future__ import annotations

import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

from app.config import Settings
from app.data_access import ShoppingDataStore
from app.graph import ShoppingAssistant
from rag.embeddings import SentenceTransformerEmbeddings
from rag.parser import parse_policy_markdown
from rag.vector_store import ChromaPolicyStore


EXAMPLE_QUESTIONS = {
    "Policy": [
        "Chính sách hoàn trả hàng ra sao?",
        "Giao hàng tiêu chuẩn thường mất bao lâu?",
        "Khách có được kiểm hàng khi nhận không?",
    ],
    "Data lookup": [
        "Đơn hàng 1971 bao giờ được giao?",
        "Cho tôi xem danh sách đơn hàng của khách hàng C001",
        "Voucher của khách hàng C001 còn những mã nào dùng được?",
    ],
    "Mixed (policy + data)": [
        "Đơn hàng 1971 có được hoàn trả không?",
        "Đơn hàng 2058 còn trong thời gian trả hàng không?",
    ],
    "Clarification": [
        "Voucher của tôi còn dùng được không?",
        "Đơn hàng của tôi có được hoàn trả không?",
    ],
    "Not found": [
        "Kiểm tra đơn hàng 9999 giúp tôi",
        "Cho tôi xem voucher của khách hàng C999",
    ],
}


@st.cache_resource(show_spinner="Loading settings...")
def load_settings() -> Settings:
    return Settings.load()


@st.cache_resource(show_spinner="Loading mock data...")
def load_data_store() -> ShoppingDataStore:
    settings = load_settings()
    return ShoppingDataStore(settings.orders_path)


@st.cache_resource(show_spinner="Loading policy index (embeddings)...")
def load_policy_store() -> ChromaPolicyStore:
    settings = load_settings()
    embedding_model = SentenceTransformerEmbeddings(settings.embedding_model_name)
    store = ChromaPolicyStore(
        persist_directory=settings.chroma_dir,
        embedding_model=embedding_model,
    )
    store.ensure_index(settings.policy_path)
    return store


@st.cache_resource(show_spinner="Loading multi-agent graph (LLM + RAG + tools)...")
def load_assistant() -> ShoppingAssistant:
    return ShoppingAssistant(settings=load_settings())


def render_route_badge(route: dict) -> None:
    if route.get("status") == "clarification_needed":
        st.warning("Route: clarification_needed")
        return

    labels: list[str] = []
    if route.get("needs_data"):
        labels.append("Data Worker")
    if route.get("needs_policy"):
        labels.append("Policy Worker")
    if not labels:
        st.info("Route: direct → Response")
        return

    st.success("Route: Supervisor → " + " → ".join(labels) + " → Response")


def render_pipeline_details(payload: dict, expanded: bool = False) -> None:
    with st.expander("Pipeline details", expanded=expanded):
        render_route_badge(payload.get("route", {}))
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Policy result**")
            st.json(payload.get("policy_result", {}))
        with col2:
            st.markdown("**Data result**")
            st.json(payload.get("data_result", {}))
        st.markdown("**Trace**")
        st.json(payload.get("trace", []))


def render_message_block(message: dict) -> None:
    role = message["role"]
    label = "You" if role == "user" else "Assistant"
    icon = "🧑" if role == "user" else "🤖"
    st.markdown(f"**{icon} {label}**")
    st.markdown(message["content"])
    if message.get("payload"):
        render_pipeline_details(message["payload"])


def run_question(question: str) -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    assistant = load_assistant()
    st.session_state.messages.append({"role": "user", "content": question})
    payload = assistant.ask(question)
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": payload.get("final_answer", ""),
            "payload": payload,
        }
    )


def process_pending_question() -> None:
    pending = st.session_state.pop("pending_question", None)
    if not pending:
        return
    with st.spinner("Running supervisor → workers → response..."):
        run_question(pending)


def render_chat_tab() -> None:
    st.subheader("Multi-Agent Chat")
    st.caption("Ask in Vietnamese. The supervisor routes to Policy RAG, Data lookup, or both.")
    st.info("First question may take ~30s while models load.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        render_message_block(message)

    st.divider()
    with st.form("chat_form", clear_on_submit=True):
        question = st.text_area(
            "Câu hỏi",
            placeholder="Ví dụ: Đơn hàng 1971 có được hoàn trả không?",
            height=90,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Gửi câu hỏi", type="primary", width="stretch")

    if submitted and question.strip():
        st.session_state.pending_question = question.strip()
        st.rerun()


def render_architecture_tab() -> None:
    st.subheader("Lab architecture")
    st.markdown(
        """
```mermaid
flowchart TD
    U[User Question] --> S[Supervisor Agent]
    S -->|policy only| P[Worker 1: Policy RAG]
    S -->|data only| D[Worker 2: Data Lookup]
    S -->|both| D
    D -->|needs policy| P
    S -->|clarification| R[Worker 3: Response]
    P --> R
    D --> R
    R --> A[Final Answer + Evidence]
```
        """
    )

    st.markdown("### Agents")
    agents = [
        ("Supervisor", "Routes by question type; detects missing order_id / customer_id"),
        ("Worker 1 — Policy", "RAG search over policy markdown via Chroma + MiniLM"),
        ("Worker 2 — Data", "4 tools: customer, orders, order detail, vouchers"),
        ("Worker 3 — Response", "Synthesizes Answer/Evidence, clarification, not_found"),
    ]
    for name, desc in agents:
        st.markdown(f"- **{name}:** {desc}")

    st.markdown("### Lab tasks completed")
    tasks = [
        "LangGraph multi-agent workflow",
        "Real RAG: H2/H3 chunking + Chroma + sentence-transformers",
        "4 small data lookup tools (not one mega-tool)",
        "Supervisor routing: policy / data / mixed / clarification",
        "Response formats: success, clarification_needed, not_found",
        "Trace JSON per run",
        "Batch test on data/test.json (22/22)",
        "Provider abstraction (OpenAI via .env)",
    ]
    for task in tasks:
        st.markdown(f"- ✅ {task}")


def render_rag_tab() -> None:
    st.subheader("Policy RAG explorer")
    st.caption("Direct search over `policy_mock_vi.md` — same index used by Worker 1.")

    settings = load_settings()
    chunks = parse_policy_markdown(settings.policy_path.read_text(encoding="utf-8"))
    st.metric("Indexed chunks", len(chunks))

    query = st.text_input("Search query", value="chính sách hoàn trả hàng 15 ngày")
    top_k = st.slider("Top K", 1, 8, settings.top_k)

    if st.button("Search policy", type="primary"):
        policy_store = load_policy_store()
        hits = policy_store.search(query, top_k=top_k)
        if not hits:
            st.warning("No hits found.")
            return
        for index, hit in enumerate(hits, start=1):
            with st.expander(
                f"#{index} · {hit.get('citation', 'N/A')} · distance={hit.get('distance', 0):.4f}"
            ):
                st.markdown(hit.get("content", ""))


def render_data_tab(store: ShoppingDataStore) -> None:
    st.subheader("Data lookup tools")
    st.caption("Worker 2 tools over `order_customer_mock_data.json`.")

    tool = st.selectbox(
        "Select tool",
        [
            "get_customer_by_id",
            "get_orders_by_customer_id",
            "get_order_detail_by_order_id",
            "get_vouchers_by_customer_id",
        ],
    )

    if tool == "get_customer_by_id":
        customer_id = st.text_input("customer_id", value="C001")
        if st.button("Lookup", type="primary"):
            st.json(store.get_customer_by_id(customer_id))

    elif tool == "get_orders_by_customer_id":
        customer_id = st.text_input("customer_id", value="C001")
        limit = st.number_input("limit", 1, 20, 10)
        if st.button("Lookup", type="primary"):
            st.json(store.get_orders_by_customer_id(customer_id, limit=limit))

    elif tool == "get_order_detail_by_order_id":
        order_id = st.text_input("order_id", value="1971")
        if st.button("Lookup", type="primary"):
            st.json(store.get_order_detail_by_order_id(order_id))

    else:
        customer_id = st.text_input("customer_id", value="C001")
        only_active = st.checkbox("only_active", value=True)
        if st.button("Lookup", type="primary"):
            st.json(store.get_vouchers_by_customer_id(customer_id, only_active=only_active))


def render_batch_tab(settings: Settings) -> None:
    st.subheader("Batch test results")
    summary_path = settings.root_dir / "src" / "artifacts" / "traces" / "summary.json"

    if not summary_path.exists():
        st.warning("No summary.json found. Run batch test from CLI first.")
        st.code(
            "set PYTHONPATH=src\r\n.venv\\Scripts\\python -m app.cli --batch --test-file data/test.json",
            language="bash",
        )
        return

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total cases", summary.get("total", 0))
    col2.metric("Route match", f"{summary.get('route_matches', 0)}/{summary.get('total', 0)}")
    col3.metric("Status match", f"{summary.get('status_matches', 0)}/{summary.get('total', 0)}")
    col4.metric("Contains match", f"{summary.get('contains_matches', 0)}/{summary.get('total', 0)}")

    rows = []
    for item in summary.get("results", []):
        rows.append(
            {
                "id": item.get("id"),
                "route_ok": item.get("route_match"),
                "status_ok": item.get("status_match"),
                "contains_ok": item.get("contains_match") if item.get("expected_contains") else True,
                "question": item.get("question", "")[:60] + "...",
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)

    selected = st.selectbox(
        "Inspect case",
        [item.get("id") for item in summary.get("results", [])],
    )
    if selected:
        match = next(item for item in summary.get("results", []) if item.get("id") == selected)
        st.json(match)


def render_report_tab(settings: Settings) -> None:
    st.subheader("Lab report")
    report_path = settings.root_dir / "REPORT.md"
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.warning("REPORT.md not found at project root.")


def main() -> None:
    st.set_page_config(
        page_title="VinShop Multi-Agent Assistant",
        page_icon="🛒",
        layout="wide",
    )

    settings = load_settings()
    store = load_data_store()

    with st.sidebar:
        st.title("VinShop Demo")
        st.caption("Day 09 · Multi-Agent Architecture")
        st.divider()
        st.markdown(f"**Provider:** `{settings.provider}`")
        st.markdown(f"**Model:** `{settings.model}`")
        st.markdown(f"**Embeddings:** `{settings.embedding_model_name}`")
        st.divider()
        st.markdown("**Example questions**")
        for group, questions in EXAMPLE_QUESTIONS.items():
            st.markdown(f"*{group}*")
            for question in questions:
                if st.button(question, key=f"ex_{question}", width="stretch"):
                    st.session_state.pending_question = question
                    st.rerun()
        st.divider()
        if st.button("Clear chat", width="stretch"):
            st.session_state.messages = []
            st.rerun()

    st.title("VinShop Multi-Agent Shopping Assistant")
    st.markdown(
        "Interactive demo for the Day 09 lab — supervisor routing, RAG, data tools, and response synthesis."
    )

    if st.session_state.get("pending_question"):
        process_pending_question()

    tab_chat, tab_arch, tab_rag, tab_data, tab_batch, tab_report = st.tabs(
        [
            "Chat",
            "Architecture",
            "Policy RAG",
            "Data tools",
            "Batch results",
            "Report",
        ]
    )

    with tab_chat:
        render_chat_tab()
    with tab_arch:
        render_architecture_tab()
    with tab_rag:
        render_rag_tab()
    with tab_data:
        render_data_tab(store)
    with tab_batch:
        render_batch_tab(settings)
    with tab_report:
        render_report_tab(settings)


if __name__ == "__main__":
    main()
