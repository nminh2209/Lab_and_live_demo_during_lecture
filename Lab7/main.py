from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from src.bootstrap import DEFAULT_SAMPLE_FILES, build_rag_system, format_search_results
from src.llm import LLM_PROVIDER_ENV


def _safe_console_text(text: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def run_manual_demo(question: str | None = None, sample_files: list[str] | None = None) -> int:
    files = sample_files or DEFAULT_SAMPLE_FILES
    query = question or "Summarize the key information from the loaded files."

    print("=== Manual File Test ===")
    print("Accepted file types: .md, .txt")
    print("Input file list:")
    for file_path in files:
        print(f"  - {file_path}")

    load_dotenv(override=False)
    llm_provider = os.getenv(LLM_PROVIDER_ENV, "mock").strip().lower()

    try:
        store, agent = build_rag_system(sample_files=files, llm_provider=llm_provider)
    except ValueError as error:
        print(f"\nSetup error: {error}")
        return 1

    embed_name = getattr(store._embedding_fn, "_backend_name", store._embedding_fn.__class__.__name__)
    llm_name = getattr(agent._llm_fn, "_backend_name", "mock demo llm")
    print(f"\nEmbedding backend: {embed_name}")
    print(f"LLM backend: {llm_name}")
    print(f"\nIndexed {store.get_collection_size()} chunks in EmbeddingStore")

    print("\n=== EmbeddingStore Search Test ===")
    print(f"Query: {query}")
    search_results = store.search(query, top_k=3)
    print(_safe_console_text(format_search_results(search_results, query=query)))

    print("\n=== KnowledgeBaseAgent Test ===")
    print(f"Question: {query}")
    print("Agent answer:")
    print(_safe_console_text(agent.answer(query, top_k=3)))
    return 0


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else None
    return run_manual_demo(question=question)


if __name__ == "__main__":
    raise SystemExit(main())
