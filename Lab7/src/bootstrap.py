from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from .agent import KnowledgeBaseAgent
from .chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from .embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from .llm import LLM_PROVIDER_ENV, create_llm_fn
from .models import Document
from .store import EmbeddingStore
from .team_strategies import (
    DocumentStructureChunker,
    ParentChildChunker,
    SemanticChunker,
    TEAM_STRATEGIES,
)

DEFAULT_SAMPLE_FILES = [
    "data/python_intro.txt",
    "data/vector_store_notes.md",
    "data/rag_system_design.md",
    "data/customer_support_playbook.txt",
    "data/chunking_experiment_report.md",
    "data/vi_retrieval_notes.md",
]


def load_documents_from_files(file_paths: list[str]) -> list[Document]:
    allowed_extensions = {".md", ".txt"}
    documents: list[Document] = []

    for raw_path in file_paths:
        path = Path(raw_path)
        if path.suffix.lower() not in allowed_extensions:
            continue
        if not path.exists() or not path.is_file():
            continue

        content = path.read_text(encoding="utf-8")
        extension = path.suffix.lower()
        category = "technical" if extension == ".md" else "reference"
        language = "vi" if "vi_" in path.name else "en"
        documents.append(
            Document(
                id=path.stem,
                content=content,
                metadata={
                    "source": str(path),
                    "extension": extension,
                    "category": category,
                    "language": language,
                    "department": "engineering" if "rag" in path.name or "vector" in path.name else "support",
                },
            )
        )

    return documents


def _build_chunker(strategy: str, config: dict[str, Any], embedding_fn: Callable[[str], list[float]] | None = None):
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=config.get("chunk_size", 400))
    if strategy == "fixed":
        return FixedSizeChunker(
            chunk_size=config.get("chunk_size", 400),
            overlap=config.get("overlap", 50),
        )
    if strategy == "sentence":
        return SentenceChunker(max_sentences_per_chunk=config.get("max_sentences", 3))
    if strategy == "parent_child":
        return ParentChildChunker(
            parent_size=config.get("parent_size", 700),
            child_size=config.get("child_size", 220),
        )
    if strategy == "document_structure":
        return DocumentStructureChunker(max_section_size=config.get("max_section_size", 500))
    if strategy == "semantic":
        if embedding_fn is None:
            raise ValueError("Semantic chunking requires an embedding function.")
        return SemanticChunker(
            embedding_fn=embedding_fn,
            similarity_threshold=config.get("similarity_threshold", 0.55),
            max_chunk_size=config.get("max_chunk_size", 500),
        )
    raise ValueError(f"Unknown chunk strategy: {strategy}")


def chunk_documents(
    documents: list[Document],
    strategy_key: str = "minh",
    embedding_fn: Callable[[str], list[float]] | None = None,
    config_override: dict[str, Any] | None = None,
) -> list[Document]:
    """Split source files using a team strategy key from TEAM_STRATEGIES."""
    config = dict(TEAM_STRATEGIES[strategy_key])
    if config_override:
        config.update(config_override)

    strategy = config["strategy"]
    chunker = _build_chunker(strategy, config, embedding_fn=embedding_fn)
    chunked: list[Document] = []

    for document in documents:
        if strategy in {"parent_child", "document_structure", "semantic"}:
            pieces = chunker.chunk(document.content)
            for index, piece in enumerate(pieces):
                metadata = dict(document.metadata)
                metadata["doc_id"] = document.id
                metadata["chunk_index"] = index
                metadata["strategy"] = strategy_key
                metadata.update(piece.metadata)
                chunked.append(
                    Document(
                        id=f"{document.id}_chunk_{index}",
                        content=piece.content,
                        metadata=metadata,
                    )
                )
        else:
            for index, piece in enumerate(chunker.chunk(document.content)):
                metadata = dict(document.metadata)
                metadata["doc_id"] = document.id
                metadata["chunk_index"] = index
                metadata["strategy"] = strategy_key
                chunked.append(
                    Document(
                        id=f"{document.id}_chunk_{index}",
                        content=piece,
                        metadata=metadata,
                    )
                )

    return chunked


def get_embedder(provider: str | None = None, api_key: str | None = None, require_openai: bool = False):
    load_dotenv(override=False)
    resolved_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    selected = (provider or os.getenv(EMBEDDING_PROVIDER_ENV, "mock")).strip().lower()

    if require_openai:
        selected = "openai"

    if selected == "mock" and resolved_key and not require_openai:
        llm_provider = os.getenv(LLM_PROVIDER_ENV, "mock").strip().lower()
        if llm_provider == "openai":
            selected = "openai"

    if selected == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            return _mock_embed
    if selected == "openai":
        if not resolved_key:
            if require_openai:
                raise ValueError("OPENAI_API_KEY is required for OpenAI benchmarks.")
            return _mock_embed
        try:
            return OpenAIEmbedder(
                model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL),
                api_key=resolved_key,
            )
        except Exception:
            if require_openai:
                raise
            return _mock_embed
    return _mock_embed


def build_rag_system(
    sample_files: list[str] | None = None,
    llm_provider: str | None = None,
    api_key: str | None = None,
    embedding_provider: str | None = None,
    collection_name: str = "rag_demo_store",
    strategy_key: str = "minh",
    require_openai: bool = False,
) -> tuple[EmbeddingStore, KnowledgeBaseAgent]:
    files = sample_files or DEFAULT_SAMPLE_FILES
    docs = load_documents_from_files(files)
    if not docs:
        raise ValueError("No documents could be loaded from the sample file list.")

    embedder = get_embedder(embedding_provider, api_key=api_key, require_openai=require_openai)
    chunks = chunk_documents(docs, strategy_key=strategy_key, embedding_fn=embedder)
    store = EmbeddingStore(collection_name=collection_name, embedding_fn=embedder)
    store.add_documents(chunks)

    llm_fn = create_llm_fn(provider=llm_provider, api_key=api_key)
    agent = KnowledgeBaseAgent(store=store, llm_fn=llm_fn)
    return store, agent


def _highlight_query_terms(text: str, query: str) -> str:
    """Bold query terms in retrieved chunk text for the UI."""
    import re

    terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    if not terms:
        return text

    highlighted = text
    for term in sorted(set(terms), key=len, reverse=True):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        highlighted = pattern.sub(lambda match: f"**{match.group(0)}**", highlighted)
    return highlighted


def format_search_results(results: list[dict], query: str = "", limit: int = 600) -> str:
    if not results:
        return "_No chunks retrieved._"

    lines: list[str] = []
    for index, item in enumerate(results, start=1):
        metadata = item.get("metadata", {})
        source = Path(metadata.get("source", "unknown")).name
        section_title = metadata.get("section_title")
        content = item["content"].strip()
        display = _highlight_query_terms(content[:limit], query)
        if len(content) > limit:
            display += "..."

        header = f"**{index}.** score=`{item['score']:.3f}` | `{source}`"
        if section_title:
            header += f" | section: `{section_title}`"

        lines.append(
            f"{header}\n\n"
            f"```md\n{display}\n```"
        )
    return "\n\n".join(lines)
