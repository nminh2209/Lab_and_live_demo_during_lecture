from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from langchain_core.tools import tool

from rag.parser import parse_policy_markdown


class ChromaPolicyStore:
    """Chroma-backed policy index."""

    def __init__(
        self,
        persist_directory: Path,
        embedding_model: Any,
        collection_name: str = "policy_chunks",
    ) -> None:
        persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(persist_directory))
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def ensure_index(self, markdown_path: Path) -> None:
        if self.collection.count() == 0:
            self.rebuild(markdown_path)

    def rebuild(self, markdown_path: Path) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except ValueError:
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

        markdown_text = markdown_path.read_text(encoding="utf-8")
        chunks = parse_policy_markdown(markdown_text)
        if not chunks:
            return

        documents = [chunk["rendered_text"] for chunk in chunks]
        embeddings = self.embedding_model.embed_documents(documents)
        ids = [f"chunk_{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "section_h2": chunk["section_h2"],
                "section_h3": chunk["section_h3"],
                "citation": chunk["citation"],
            }
            for chunk in chunks
        ]
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        if self.collection.count() == 0:
            return []

        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict[str, Any]] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for document, metadata, distance in zip(documents, metadatas, distances):
            hits.append(
                {
                    "citation": metadata.get("citation", ""),
                    "content": document,
                    "distance": distance,
                    "section_h2": metadata.get("section_h2", ""),
                    "section_h3": metadata.get("section_h3", ""),
                }
            )
        return hits


def build_policy_search_tool(store: ChromaPolicyStore, top_k: int):
    @tool
    def search_policy(query: str) -> list[dict[str, Any]]:
        """Search the shopping policy knowledge base and return top relevant chunks."""
        return store.search(query, top_k=top_k)

    return search_policy
