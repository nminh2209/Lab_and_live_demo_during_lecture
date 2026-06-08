from pathlib import Path
from typing import Callable

from .store import EmbeddingStore

_THIN_CHUNK_CHARS = 120


def _build_context_block(result: dict) -> str:
    """Format one retrieved chunk for the LLM, enriching thin chunks when possible."""
    metadata = result.get("metadata", {})
    content = result.get("content", "").strip()

    parent_preview = str(metadata.get("parent_preview", "")).strip()
    if len(content) < _THIN_CHUNK_CHARS and parent_preview and parent_preview not in content:
        content = f"{parent_preview}\n\n{content}"

    source = Path(metadata.get("source", "unknown")).name
    labels = [f"source={source}"]
    section_title = str(metadata.get("section_title", "")).strip()
    if section_title:
        labels.append(f"section={section_title}")

    return f"[{' | '.join(labels)}]\n{content}"


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self._store = store
        self._llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self._store.search(question, top_k=top_k)
        if not results:
            return "No relevant context was retrieved for this question."

        context_blocks = [_build_context_block(result) for result in results]
        context = "\n\n---\n\n".join(context_blocks)

        prompt = (
            "Use the following retrieved context to answer the question.\n"
            "You may summarize and combine information across chunks.\n"
            "If the context describes related concepts, explain them even when "
            "there is no single formal definition sentence.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
        return self._llm_fn(prompt)
