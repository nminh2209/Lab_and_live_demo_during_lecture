"""Run Minh's strategy benchmark with OpenAI LLM + embeddings."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.bootstrap import build_rag_system

store, agent = build_rag_system(
    llm_provider="openai",
    strategy_key="minh",
    require_openai=True,
)

print(f"CHUNKS={store.get_collection_size()}")
print(f"EMBED={getattr(store._embedding_fn, '_backend_name', '?')}")

queries = [
    ("What is Python used for?", None),
    ("How does a vector store work?", None),
    ("What is the RAG system architecture?", None),
    ("What are common customer support issues?", None),
    ("What are common retrieval failure cases in Vietnamese?", {"language": "vi"}),
]

for query, metadata_filter in queries:
    print(f"\nQUERY={query}")
    if metadata_filter:
        results = store.search_with_filter(query, top_k=3, metadata_filter=metadata_filter)
        print(f"FILTER={metadata_filter}")
    else:
        results = store.search(query, top_k=3)

    for index, item in enumerate(results, start=1):
        source = Path(item["metadata"].get("source", "unknown")).name
        preview = item["content"][:100].replace("\n", " ")
        print(f"  TOP{index} score={item['score']:.3f} source={source}")
        print(f"       preview={preview}")

    answer = agent.answer(query, top_k=3)
    print(f"  ANSWER={answer[:300].replace(chr(10), ' ')}")
