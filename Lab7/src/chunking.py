from __future__ import annotations

import math
import re

_HEADING_ONLY = re.compile(r"^#{1,6}\s+\S.+$")


def merge_heading_only_chunks(chunks: list[str]) -> list[str]:
    """
    Merge markdown heading-only chunks with the following chunk.

    Recursive splitting on paragraph breaks often isolates lines like
    ``## Section Title`` from their body text — bad for retrieval.
    """
    if not chunks:
        return []

    merged: list[str] = []
    index = 0
    while index < len(chunks):
        current = chunks[index].strip()
        is_heading_only = bool(_HEADING_ONLY.match(current)) and "\n" not in current
        if is_heading_only and index + 1 < len(chunks):
            combined = f"{current}\n\n{chunks[index + 1].strip()}"
            merged.append(combined)
            index += 2
        else:
            merged.append(chunks[index])
            index += 1
    return merged


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    _SENTENCE_SPLIT = re.compile(r"(?<=[.!?])(?:\s+|\n)")

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = [
            sentence.strip()
            for sentence in self._SENTENCE_SPLIT.split(text.strip())
            if sentence.strip()
        ]
        if not sentences:
            return []

        chunks: list[str] = []
        for start in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[start : start + self.max_sentences_per_chunk]
            chunks.append(" ".join(group))
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if not self.separators:
            return [
                text[index : index + self.chunk_size]
                for index in range(0, len(text), self.chunk_size)
            ]
        return merge_heading_only_chunks(self._split(text, self.separators))

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text] if current_text else []

        if not remaining_separators:
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]

        if separator == "":
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]

        if separator not in current_text:
            return self._split(current_text, next_separators)

        splits = current_text.split(separator)
        chunks: list[str] = []
        current_parts: list[str] = []

        for index, split in enumerate(splits):
            piece = split
            piece_len = len(piece) + (len(separator) if index < len(splits) - 1 else 0)

            if piece_len > self.chunk_size:
                if current_parts:
                    chunks.append(separator.join(current_parts))
                    current_parts = []
                chunks.extend(self._split(piece, next_separators))
                continue

            candidate = separator.join(current_parts + [piece]) if current_parts else piece
            if len(candidate) <= self.chunk_size:
                current_parts.append(piece)
            else:
                if current_parts:
                    chunks.append(separator.join(current_parts))
                current_parts = [piece]

        if current_parts:
            chunks.append(separator.join(current_parts))

        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(sum(value * value for value in vec_a))
    norm_b = math.sqrt(sum(value * value for value in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        result: dict[str, dict] = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = sum(len(chunk) for chunk in chunks) / count if count else 0.0
            result[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return result
