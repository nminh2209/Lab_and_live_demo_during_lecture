# Group Report — Lab 18: Production RAG

**Nhóm:** Production RAG Batch 2  
**Ngày:** 22/06/2026  
**Thành viên:** Nguyễn Hoàng Minh (implement toàn bộ M1–M5)

---

## Thành viên & Phân công

| Tên | Module | Hoàn thành | Tests pass |
|-----|--------|-----------|-----------|
| Nguyễn Hoàng Minh | M1: Chunking | ✅ | 13/13 |
| Nguyễn Hoàng Minh | M2: Hybrid Search | ✅ | 5/5 |
| Nguyễn Hoàng Minh | M3: Reranking | ✅ | 5/5 |
| Nguyễn Hoàng Minh | M4: Evaluation | ✅ | 4/4 |
| Nguyễn Hoàng Minh | M5: Enrichment | ✅ | 10/10 |

**Tổng:** 37/37 tests pass · Pipeline end-to-end exit code 0

---

## Kết quả RAGAS

| Metric | Naive Baseline | Production | Δ | Ngưỡng 0.70 |
|--------|---------------|------------|---|-------------|
| Faithfulness | 0.8167 | 0.7250 | -0.0917 | Prod ✗ |
| Answer Relevancy | 0.7203 | 0.7209 | +0.0007 | Prod ✓ |
| Context Precision | 0.9250 | 0.8875 | -0.0375 | Prod ✓ |
| Context Recall | 0.9250 | 0.7917 | -0.1333 | Prod ✓ |

**Điểm RAGAS theo rubric:** 3/4 metrics ≥ 0.70 trên production → **10/10 điểm mục #7**

---

## Key Findings

1. **Biggest improvement:** Answer relevancy giữ nguyên (~0.72) dù pipeline phức tạp hơn nhiều; context precision vẫn cao (0.89) nhờ hybrid search + reranking lọc noise.
2. **Biggest challenge:** Context recall giảm **13.3 điểm %** — hierarchical child chunks (256 chars) thiếu ngữ cảnh so với paragraph baseline (500 chars). Multi-hop và cross-document questions bị ảnh hưởng nặng.
3. **Surprise finding:** Baseline đơn giản **thắng** production về faithfulness (0.82 vs 0.73). Nhiều lỗi là **generation** (trả "Không tìm thấy" dù context đã đủ), không phải retrieval.

---

## Presentation Notes (5 phút)

1. **RAGAS scores:** Production không tự động tốt hơn — phải đo. 2 metrics retrieval (precision/recall) vẫn OK; faithfulness tụt do prompt + chunk size.
2. **Biggest win — M2 Hybrid + M3 Rerank:** BM25 bắt keyword tiếng Việt ("55 triệu", "nghỉ phép"); RRF merge với dense; cross-encoder đẩy doc liên quan lên top-3.
3. **Case study:** "Nhân viên thử việc có được nghỉ phép năm không?" — recall=1.0 nhưng trả "Không tìm thấy". Error Tree: lỗi generation, fix prompt CÓ/KHÔNG.
4. **Next optimization (1 giờ):** Tăng child chunk → 512; retrieve child / return parent; sửa system prompt; filter metadata `version=v2024`.

---

*Báo cáo chi tiết đầy đủ: [`reports/lab18_detailed_report.md`](../reports/lab18_detailed_report.md)*
