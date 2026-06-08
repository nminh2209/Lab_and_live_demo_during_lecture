"""
Gradio UI for Day 7 RAG demo with team chunking strategies.

Run:
    pip install gradio openai
    python app.py
"""

from __future__ import annotations

import os

import gradio as gr
from dotenv import load_dotenv

from src.bootstrap import build_rag_system, format_search_results
from src.llm import LLM_PROVIDER_ENV, OPENAI_LLM_MODEL
from src.team_strategies import TEAM_STRATEGIES

load_dotenv(override=False)

_store = None
_agent = None
_backend_label = "not loaded"
_current_strategy = "minh"

STRATEGY_CHOICES = {
    "minh": "Minh — Recursive character splitting",
    "duy": "Duy — Parent/child chunking",
    "nam": "Nam — Document-structure chunking",
    "dung": "Dũng — Semantic chunking",
}


def _ensure_agent(llm_provider: str, api_key: str, strategy_key: str):
    global _store, _agent, _backend_label, _current_strategy

    provider = llm_provider.strip().lower()
    key = api_key.strip() or None
    strategy_key = strategy_key.strip().lower()

    if _store is not None and strategy_key == _current_strategy and _agent is not None:
        return

    use_openai = provider == "openai" or bool(key or os.getenv("OPENAI_API_KEY"))
    _store, _agent = build_rag_system(
        llm_provider=provider,
        api_key=key,
        collection_name=f"ui_{strategy_key}",
        strategy_key=strategy_key,
        require_openai=use_openai,
        embedding_provider="openai" if use_openai else "mock",
    )
    _current_strategy = strategy_key

    llm_name = getattr(_agent._llm_fn, "_backend_name", "mock")
    embed_name = getattr(_store._embedding_fn, "_backend_name", _store._embedding_fn.__class__.__name__)
    strategy_label = TEAM_STRATEGIES[strategy_key]["label"]
    _backend_label = (
        f"Strategy: {strategy_label} | LLM: {llm_name} | "
        f"Embeddings: {embed_name} | Chunks: {_store.get_collection_size()}"
    )


def ask(
    question: str,
    top_k: int,
    llm_provider: str,
    api_key: str,
    strategy_key: str,
) -> tuple[str, str, str]:
    if not question.strip():
        return "Please enter a question.", "", _backend_label

    try:
        _ensure_agent(llm_provider, api_key, strategy_key)
        results = _store.search(question.strip(), top_k=int(top_k))
        answer = _agent.answer(question.strip(), top_k=int(top_k))
        return answer, format_search_results(results, query=question.strip()), _backend_label
    except ValueError as error:
        return str(error), "", _backend_label
    except Exception as error:
        return f"Error: {error}", "", _backend_label


def build_ui() -> gr.Blocks:
    default_provider = os.getenv(LLM_PROVIDER_ENV, "openai").strip().lower()
    if default_provider not in {"mock", "openai"}:
        default_provider = "openai"

    with gr.Blocks(title="Day 7 RAG Demo") as demo:
        gr.Markdown(
            "# Knowledge Base Agent\n"
            "Compare team chunking strategies on the same `data/` corpus.\n\n"
            f"- **Minh**: recursive character splitting\n"
            f"- **Duy**: parent/child chunking\n"
            f"- **Nam**: document-structure (markdown headings)\n"
            f"- **Dũng**: semantic chunking (OpenAI embeddings during chunk)\n\n"
            f"Set `OPENAI_API_KEY` in `.env` for real embeddings and **{OPENAI_LLM_MODEL}** answers."
        )

        with gr.Row():
            strategy = gr.Dropdown(
                choices=list(STRATEGY_CHOICES.keys()),
                value="minh",
                label="Chunking strategy",
                info="Select team member's method",
            )
            llm_provider = gr.Dropdown(
                choices=["mock", "openai"],
                value=default_provider,
                label="LLM Provider",
            )
            api_key = gr.Textbox(
                label="OpenAI API Key (optional if set in .env)",
                placeholder="sk-...",
                type="password",
            )

        question = gr.Textbox(
            label="Question",
            placeholder="What is Python used for?",
            lines=2,
        )
        top_k = gr.Slider(minimum=1, maximum=8, value=3, step=1, label="Top-k chunks")
        submit = gr.Button("Ask", variant="primary")

        backend = gr.Textbox(label="Active setup", interactive=False)
        answer = gr.Textbox(label="Agent answer", lines=8)
        sources = gr.Markdown(label="Retrieved chunks")

        examples = gr.Examples(
            examples=[
                ["What is Python used for?", 3, default_provider, "", "minh"],
                ["How does a vector store workflow work?", 3, default_provider, "", "duy"],
                ["What is the proposed RAG architecture?", 3, default_provider, "", "nam"],
                ["What customer support topics should be indexed?", 3, default_provider, "", "duy"],
                ["What are common retrieval failure cases?", 3, default_provider, "", "dung"],
                ["What is chunking?", 3, default_provider, "", "duy"],
            ],
            inputs=[question, top_k, llm_provider, api_key, strategy],
        )

        submit.click(
            ask,
            inputs=[question, top_k, llm_provider, api_key, strategy],
            outputs=[answer, sources, backend],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860)
