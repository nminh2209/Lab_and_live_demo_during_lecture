# Day 09 — Multi-Agent Shopping Assistant

**Lab:** VinShop Demo Multi-Agent Architecture  
**Stack:** LangGraph · OpenAI · Chroma · sentence-transformers  
**Provider:** OpenAI (`gpt-4.1-mini`) via `.env`

---

## 1. Project summary

I built an end-to-end **customer support shopping assistant** that answers Vietnamese questions about:

- **Policy** — shipping, returns, vouchers (from `data/policy_mock_vi.md` via RAG)
- **Order / customer / voucher data** — lookups from `data/order_customer_mock_data.json`
- **Mixed questions** — combines policy rules with real order/customer facts

Example: *"Đơn hàng 1971 có được hoàn trả không?"* → fetches order `1971` (in transit) and return policy (15-day window) → explains the order cannot be returned yet.

---

## 2. Architecture

```
User Question
     │
     ▼
┌─────────────┐
│  Supervisor │  route: policy / data / both / clarification
└──────┬──────┘
       │
   ┌───┴────────────────┐
   ▼                    ▼
┌──────────┐      ┌──────────┐
│ Worker 1 │      │ Worker 2 │
│ Policy   │      │ Data     │
│ RAG      │      │ 4 tools  │
└────┬─────┘      └────┬─────┘
     │    (data → policy when both)
     └────────┬────────┘
              ▼
       ┌─────────────┐
       │  Worker 3   │  final answer + evidence
       │  Response   │
       └─────────────┘
```

| Agent | File | Responsibility |
|-------|------|----------------|
| Supervisor | `src/app/graph.py` | Route by question type; detect missing IDs |
| Worker 1 — Policy | `src/app/graph.py` + `src/rag/` | `search_policy` over Chroma index |
| Worker 2 — Data | `src/app/data_access.py` | 4 small lookup tools |
| Worker 3 — Response | `src/app/graph.py` | Answer / Evidence / clarification / not_found |

---

## 3. Implementation checklist

| Task | Status | Details |
|------|--------|---------|
| Supervisor routing | ✅ | LLM + `_normalize_route()` heuristics for IDs |
| Policy RAG (Worker 1) | ✅ | H2/H3 chunking, Chroma, `all-MiniLM-L6-v2` |
| Data tools (Worker 2) | ✅ | 4 separate LangChain tools |
| Response synthesis (Worker 3) | ✅ | 3 output formats with Policy / Order evidence |
| `clarification_needed` | ✅ | Q15, Q16 |
| `not_found` | ✅ | Q17, Q18 |
| Trace JSON | ✅ | Per-step logs in `src/artifacts/traces/` |
| Batch test | ✅ | `data/test.json` → `summary.json` |
| Provider abstraction | ✅ | OpenAI (swappable via `LLM_PROVIDER`) |
| Prompts per agent | ✅ | `src/app/prompts.py` |

### Data tools

1. `get_customer_by_id` — tier, voucher quota
2. `get_orders_by_customer_id` — recent orders
3. `get_order_detail_by_order_id` — status, delivery, return eligibility
4. `get_vouchers_by_customer_id` — active voucher codes

### RAG pipeline

- **Parser:** `src/rag/parser.py` — chunks by `## H2` + `### H3` + content (33 chunks)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`
- **Vector store:** Chroma persistent index at `src/.chroma`
- **Search output:** `citation`, `content`, `distance`

---

## 4. Test results

**Batch run:** `2026-06-09` · 22 test cases from `data/test.json`

| Metric | Result |
|--------|--------|
| Route match | **22 / 22** |
| Status match | **22 / 22** |
| Contains match | **22 / 22** |

Full results: `src/artifacts/traces/summary.json`

### Sample cases covered

| Type | Example | Result |
|------|---------|--------|
| Policy | Chính sách hoàn trả hàng ra sao? | ✅ |
| Data | Đơn hàng 1971 bao giờ được giao? | ✅ |
| Mixed | Đơn hàng 1971 có được hoàn trả không? | ✅ |
| Clarification | Voucher của tôi còn dùng được không? | ✅ |
| Not found | Kiểm tra đơn hàng 9999 giúp tôi | ✅ |

---

## 5. Rubric self-assessment

| Section | Points | Score |
|---------|--------|-------|
| Core lab (Supervisor, RAG, 4 tools, Response) | 60 | **60** |
| Engineering (chunking, Chroma, clarification, not_found, batch) | 30 | **30** |
| Bonus (citations, trace, provider, prompts) | 10 | **10** |
| Penalties | — | **0** |
| **Total** | **100** | **100** |

---

## 6. How to run

### CLI — single question

```powershell
cd e:\VinAI\Day09-MultiAgent-Architecture
$env:PYTHONPATH="src"
.\.venv\Scripts\python -m app.cli --question "Đơn hàng 1971 có được hoàn trả không?"
```

### CLI — batch test

```powershell
$env:PYTHONPATH="src"
.\.venv\Scripts\python -m app.cli --batch --test-file data/test.json
```

### Streamlit demo UI

```powershell
$env:PYTHONPATH="src"
.\.venv\Scripts\streamlit run src/streamlit_app.py
```

### Environment (`.env`)

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your_key_here
```

---

## 7. Key files

| Path | Purpose |
|------|---------|
| `src/app/graph.py` | LangGraph orchestration + `ShoppingAssistant` |
| `src/app/data_access.py` | Mock data store + 4 tools |
| `src/app/prompts.py` | Agent prompts |
| `src/rag/parser.py` | Policy markdown chunking |
| `src/rag/vector_store.py` | Chroma index + search |
| `src/provider/` | LLM provider abstraction |
| `src/streamlit_app.py` | Interactive demo UI |
| `data/test.json` | 22 evaluation cases |
| `src/artifacts/traces/summary.json` | Latest batch results |

---

## 8. Demo UI features

The Streamlit app showcases every lab deliverable:

- **Chat** — live multi-agent Q&A with pipeline trace
- **Architecture** — supervisor + 3 workers flow
- **Policy RAG** — direct chunk search with citations
- **Data tools** — interactive lookup for all 4 tools
- **Batch results** — 22/22 test score table
- **Report** — this document inline

---

*Generated for Day 09 Multi-Agent Architecture lab submission.*
