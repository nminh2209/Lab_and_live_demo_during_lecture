from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .chunking import RecursiveChunker, SentenceChunker, compute_similarity, merge_heading_only_chunks


@dataclass
class ChunkPiece:
    """One indexed chunk with optional extra metadata."""

    content: str
    metadata: dict


class ParentChildChunker:
    """
    Parent/child chunking (Duy).

    - Parent: larger segments (section-level context).
    - Child: smaller segments used for retrieval; metadata stores parent text.
  """

    def __init__(
        self,
        parent_size: int = 700,
        child_size: int = 220,
    ) -> None:
        self._parent_chunker = RecursiveChunker(chunk_size=parent_size)
        self._child_chunker = RecursiveChunker(chunk_size=child_size)

    def chunk(self, text: str) -> list[ChunkPiece]:
        if not text:
            return []

        pieces: list[ChunkPiece] = []
        for parent_index, parent_text in enumerate(self._parent_chunker.chunk(text)):
            children = self._child_chunker.chunk(parent_text)
            for child_index, child_text in enumerate(children):
                pieces.append(
                    ChunkPiece(
                        content=child_text,
                        metadata={
                            "chunk_role": "child",
                            "parent_index": parent_index,
                            "child_index": child_index,
                            "parent_preview": parent_text[:300],
                        },
                    )
                )
        return _merge_thin_pieces(pieces)


def _merge_thin_pieces(pieces: list[ChunkPiece]) -> list[ChunkPiece]:
    """Merge heading-only or very short chunks with the next piece."""
    if not pieces:
        return []

    texts = [piece.content for piece in pieces]
    merged_texts = merge_heading_only_chunks(texts)

    if len(merged_texts) == len(pieces):
        return pieces

    merged: list[ChunkPiece] = []
    source_index = 0
    for merged_text in merged_texts:
        if source_index < len(pieces) and pieces[source_index].content.strip() == merged_text.strip():
            merged.append(pieces[source_index])
            source_index += 1
            continue

        combined_meta = dict(pieces[min(source_index, len(pieces) - 1)].metadata)
        if source_index + 1 < len(pieces):
            combined_meta.update(pieces[source_index + 1].metadata)
        merged.append(ChunkPiece(content=merged_text, metadata=combined_meta))
        source_index += 2 if source_index + 1 < len(pieces) else 1

    return merged


class DocumentStructureChunker:
    """
    Document-structure chunking (Nam).

    Splits on markdown headings (#, ##, ###). Long sections are split recursively.
    """

    _HEADER_PATTERN = re.compile(r"(?=^#{1,3}\s+)", re.MULTILINE)

    def __init__(self, max_section_size: int = 500) -> None:
        self.max_section_size = max_section_size
        self._fallback = RecursiveChunker(chunk_size=max_section_size)

    def chunk(self, text: str) -> list[ChunkPiece]:
        if not text:
            return []

        sections = [
            section.strip()
            for section in self._HEADER_PATTERN.split(text.strip())
            if section.strip()
        ]
        if not sections:
            sections = [text.strip()]

        pieces: list[ChunkPiece] = []
        for index, section in enumerate(sections):
            title_match = re.match(r"^(#{1,3}\s+.+)", section)
            section_title = title_match.group(1).strip() if title_match else f"section_{index}"

            if len(section) <= self.max_section_size:
                sub_chunks = [section]
            else:
                sub_chunks = self._fallback.chunk(section)

            for sub_index, sub_chunk in enumerate(sub_chunks):
                pieces.append(
                    ChunkPiece(
                        content=sub_chunk,
                        metadata={
                            "section_title": section_title,
                            "section_index": index,
                            "sub_index": sub_index,
                        },
                    )
                )
        return _merge_thin_pieces(pieces)


class SemanticChunker:
    """
    Semantic chunking (Dũng).

    Groups consecutive sentences while embedding similarity stays above threshold.
    Requires an embedding function (OpenAI in production benchmarks).
    """

    _SENTENCE_SPLIT = re.compile(r"(?<=[.!?])(?:\s+|\n)")

    def __init__(
        self,
        embedding_fn: Callable[[str], list[float]],
        similarity_threshold: float = 0.55,
        max_chunk_size: int = 500,
    ) -> None:
        self.embedding_fn = embedding_fn
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size

    def _sentences(self, text: str) -> list[str]:
        parts = [
            sentence.strip()
            for sentence in self._SENTENCE_SPLIT.split(text.strip())
            if sentence.strip()
        ]
        return parts if parts else ([text.strip()] if text.strip() else [])

    def chunk(self, text: str) -> list[ChunkPiece]:
        if not text:
            return []

        sentences = self._sentences(text)
        if len(sentences) == 1:
            return [ChunkPiece(content=sentences[0], metadata={"chunking": "semantic"})]

        embeddings = [self.embedding_fn(sentence) for sentence in sentences]
        groups: list[list[str]] = [[sentences[0]]]

        for index in range(1, len(sentences)):
            similarity = compute_similarity(embeddings[index - 1], embeddings[index])
            candidate = " ".join(groups[-1] + [sentences[index]])
            if similarity >= self.similarity_threshold and len(candidate) <= self.max_chunk_size:
                groups[-1].append(sentences[index])
            else:
                groups.append([sentences[index]])

        return [
            ChunkPiece(content=" ".join(group), metadata={"chunking": "semantic", "sentence_count": len(group)})
            for group in groups
        ]


# Team registry used by bootstrap + compare script
TEAM_STRATEGIES: dict[str, dict] = {
    "minh": {
        "member": "Minh",
        "label": "Recursive character splitting",
        "strategy": "recursive",
        "chunk_size": 400,
    },
    "duy": {
        "member": "Duy",
        "label": "Parent/child chunking",
        "strategy": "parent_child",
        "parent_size": 700,
        "child_size": 220,
    },
    "nam": {
        "member": "Nam",
        "label": "Document-structure chunking",
        "strategy": "document_structure",
        "max_section_size": 500,
    },
    "dung": {
        "member": "Dũng",
        "label": "Semantic chunking",
        "strategy": "semantic",
        "similarity_threshold": 0.55,
        "max_chunk_size": 500,
    },
    "baseline_fixed": {
        "member": "Baseline",
        "label": "Fixed-size chunking",
        "strategy": "fixed",
        "chunk_size": 400,
        "overlap": 50,
    },
    "baseline_sentence": {
        "member": "Baseline",
        "label": "Sentence chunking",
        "strategy": "sentence",
        "max_sentences": 3,
    },
}
