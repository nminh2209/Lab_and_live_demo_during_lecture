import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from main import SAMPLE_FILES, load_documents_from_files
from src.chunking import ChunkingStrategyComparator, compute_similarity
from src.embeddings import _mock_embed
from src.store import EmbeddingStore

for file_path in SAMPLE_FILES:
    text = (ROOT / file_path).read_text(encoding="utf-8")
    print(f"SIZE {Path(file_path).name}: {len(text)}")

comparator = ChunkingStrategyComparator()
for file_path in SAMPLE_FILES[:3]:
    text = (ROOT / file_path).read_text(encoding="utf-8")
    result = comparator.compare(text, chunk_size=200)
    print(f"CHUNK {Path(file_path).name}")
    for name, stats in result.items():
        print(f"  {name}: count={stats['count']}, avg={stats['avg_length']:.1f}")

pairs = [
    ("Python is a programming language.", "Python is widely used for software development."),
    ("The cat sat on the mat.", "Stock prices rose sharply today."),
    ("Vector databases store embeddings.", "A vector store keeps numerical representations of text."),
    ("How do I reset my password?", "Password recovery requires email verification."),
    ("Machine learning uses neural networks.", "Deep learning models have many layers."),
]
print("SIMILARITY")
for sentence_a, sentence_b in pairs:
    score = compute_similarity(_mock_embed(sentence_a), _mock_embed(sentence_b))
    print(f"  {score:.4f} | A={sentence_a} | B={sentence_b}")

docs = load_documents_from_files([str(ROOT / f) for f in SAMPLE_FILES])
store = EmbeddingStore("bench", _mock_embed)
store.add_documents(docs)
queries = [
    "What is Python used for?",
    "How does a vector store work?",
    "What is the RAG system architecture?",
    "What are common customer support issues?",
    "What are common retrieval failure cases in Vietnamese?",
]
print("BENCHMARK")
for query in queries:
    results = store.search(query, top_k=3)
    print(f"Q: {query}")
    for index, item in enumerate(results, start=1):
        source = Path(item["metadata"].get("source", "?")).name
        preview = item["content"][:90].replace("\n", " ")
        print(f"  {index}. score={item['score']:.3f} src={source} preview={preview}...")
