# Individual Reflection — Lab 18: Production RAG

**Tên:** Nguyễn Hoàng Minh  
**Ngày:** 22/06/2026  
**Lab:** Day 18 — Production RAG Pipeline (AICB-P2T3)

---

## Phần 1: Mapping bài giảng → Code

| Lecture Concept | Module | Hàm cụ thể | Observation |
|-----------------|--------|------------|-------------|
| Semantic chunking | M1 | `chunk_semantic()` | Dùng `all-MiniLM-L6-v2` + cosine similarity threshold 0.85. Với corpus HR tiếng Việt, semantic tạo ít chunk hơn basic (~gộp câu cùng chủ đề) nhưng encode 26 docs mất vài giây — trade-off latency vs chất lượng cắt chunk. |
| Hierarchical parent-child | M1 | `chunk_hierarchical()` | Parent 2048 chars / child 256 chars. Pipeline index **child** để retrieve chính xác, nhưng RAGAS **context recall giảm 13%** (0.925 → 0.792) vì child quá nhỏ, thiếu ngữ cảnh so với baseline paragraph chunking. |
| Structure-aware chunking | M1 | `chunk_structure_aware()` | Parse `#{1,3}` headers → mỗi section 1 chunk, metadata `section` giữ tiêu đề. Hữu ích cho policy có bảng/ngưỡng phê duyệt — nên kết hợp với hierarchical thay vì chỉ child fixed-size. |
| BM25 + Vietnamese segmentation | M2 | `segment_vietnamese()`, `BM25Search` | `underthesea` nối từ ghép bằng `_` → **bắt buộc** `replace("_", " ")` để query "nghỉ phép" khớp corpus. BM25 bắt keyword tốt cho số liệu ("55 triệu", "50.000.000"). |
| Dense + Hybrid RRF | M2 | `DenseSearch`, `reciprocal_rank_fusion()` | `bge-m3` + Qdrant `query_points()`. RRF (k=60) merge BM25+dense — doc xuất hiện cả 2 list được boost. Context precision production vẫn cao (0.887). |
| Cross-encoder reranking | M3 | `CrossEncoderReranker.rerank()` | `BAAI/bge-reranker-v2-m3` qua `sentence_transformers.CrossEncoder` (không dùng FlagEmbedding). Top-20 → top-3. Query "nghỉ phép" rank đúng trước "VPN" trong unit test; latency ~vài trăm ms/query trên CPU. |
| RAGAS 4 metrics | M4 | `evaluate_ragas()`, `failure_analysis()` | 20 câu test × 4 metrics. Metric thấp nhất: **faithfulness (0.725)** — nhiều câu negation/multi-hop. `failure_analysis()` map worst metric → diagnostic tree (hallucination / missing chunks / bad prompt). |
| Contextual enrichment (combined) | M5 | `_enrich_single_call()`, `enrich_chunks()` | 1 GPT-4o-mini call/chunk → summary + HyQA + context prepend + metadata. 100 chunks ≈ **397s** enrichment. Bonus mode combined thay vì 4 calls/chunk. Fallback extractive khi không có API key. |

---

## Phần 2: Khó khăn & Cách giải quyết

### 2.1 Môi trường & dependency

| Lỗi | Cách debug | Giải pháp |
|-----|------------|----------|
| `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4cc'` khi chạy `main.py` trên Windows | Traceback chỉ vào `print()` emoji trong `main.py` line 24 | Set `$env:PYTHONIOENCODING="utf-8"` và `$env:PYTHONUTF8="1"` trước khi chạy |
| `pip install` timeout / numpy build fail trên Python 3.13 | `NumPy requires GCC >= 8.4` khi build từ source | Tạo `.venv` với **Python 3.12** (`py -3.12 -m venv .venv`), cài deps trong venv |
| `failed to connect to the docker API` | `docker compose ps` trả lỗi npipe | Start Docker Desktop, chờ daemon ready, rồi `docker compose up -d` cho Qdrant |

**Thời gian debug môi trường:** ~45 phút (chủ yếu pip download torch + chờ Docker).

### 2.2 Kỹ thuật RAG

| Lỗi / hiện tượng | Cách debug | Giải pháp / học được |
|------------------|------------|----------------------|
| Production **thua** baseline về faithfulness & recall | So sánh `reports/naive_baseline_report.json` vs `reports/ragas_report.json`; đọc bottom failures | Child chunk 256 chars mất context; prompt "Không tìm thấy" quá bảo thủ → model bỏ qua câu trả lời phủ định dù recall=1.0 |
| Câu "thử việc có nghỉ phép không?" → "Không tìm thấy" | Error Tree: context recall 1.0 nhưng faithfulness 0 | Lỗi **generation**, không phải retrieval — cần prompt CÓ/KHÔNG rõ ràng |
| `underthesea` BM25 không match "nghỉ phép" | In `segment_vietnamese()` → thấy `nghỉ_phép` 1 token | `replace("_", " ")` theo gợi ý trong scaffold |
| RAGAS chạy lâu (~50s baseline, ~37s production eval) | Log tqdm `Evaluating: 80/80` | Bình thường — mỗi metric gọi LLM judge; cần `OPENAI_API_KEY` |

### 2.3 Kiến thức thiếu → cách bổ sung

- **Parent-child retrieval pattern:** Đọc thêm Anthropic contextual retrieval + hierarchical RAG papers; thực hành retrieve child → return parent text.
- **RAGAS interpretation:** Metric thấp không luôn = retrieval sai — phải xem per-question breakdown trong `ragas_report.json`.
- **Vietnamese NLP:** Thử `pyvi` / `underthesea` format khác cho BM25 tokenization.

---

## Phần 3: Action Plan cho project cá nhân

## Project: Chatbot tra cứu nội quy / tài liệu nội bộ (HR & IT policy)

### Hiện tại

- RAG pipeline hiện tại: paragraph chunking + OpenAI embedding + vector search đơn giản (tương tự naive baseline).
- Known issues:
  - Câu hỏi phủ định ("có được ... không?") trả lời mơ hồ.
  - Policy có nhiều version (v2023 vs v2024) — model lấy nhầm bản cũ.
  - Không có evaluation tự động, chỉ test thủ công.

### Plan áp dụng (từ Lab 18)

1. [ ] **Chunking:** Hierarchical parent-child + structure-aware cho file `.md` có headers. Giữ parent 2048 / child 512 (tăng từ 256) để cải thiện recall.
2. [ ] **Search:** Hybrid BM25 + dense + RRF. Segment tiếng Việt với `underthesea`, replace `_`.
3. [ ] **Reranking:** Cross-encoder `bge-reranker-v2-m3`, top-20 → top-3 trước khi đưa vào LLM.
4. [ ] **Evaluation:** RAGAS trên 20–30 câu golden Q&A; chạy sau mỗi thay đổi pipeline. Theo dõi faithfulness riêng cho câu negation.
5. [ ] **Enrichment:** Combined single-call enrichment + metadata `version`, `category` để filter retrieval.

### Timeline

| Tuần | Việc |
|------|------|
| Tuần 1 | Migrate corpus sang hierarchical chunking; setup Qdrant + hybrid search |
| Tuần 2 | Thêm reranker + sửa prompt generation (CÓ/KHÔNG, cite source) |
| Tuần 3 | Xây test set 30 câu + tích hợp RAGAS CI; enrichment + version metadata |
| Tuần 4 | Streamlit demo nội bộ + failure analysis định kỳ; optimize latency enrichment (batch API) |

### Tự đánh giá

| Tiêu chí | Tự chấm (1-5) | Ghi chú |
|----------|---------------|---------|
| Hiểu bài giảng | 4 | Nắm được flow M1→M5; cần đọc thêm parent-child retrieval |
| Code quality | 4 | Pass 37/37 tests; còn optimize pipeline latency |
| Teamwork | N/A | Lab cá nhân |
| Problem solving | 4 | Debug được encoding, venv, Docker, và phân tích RAGAS failures |

---

## Đóng góp kỹ thuật (tóm tắt)

- **Modules implement:** M1 (chunking), M2 (hybrid search), M3 (rerank), M4 (RAGAS eval), M5 (enrichment combined mode), `pipeline.py` end-to-end.
- **Kết quả chạy thực tế:** 37/37 pytest pass; pipeline ~22 phút (100 chunks enrichment + 20 queries RAGAS).
- **Insight quan trọng nhất:** Production pipeline phức tạp hơn không tự động tốt hơn — phải đo bằng RAGAS và phân tích failure trước khi deploy.
