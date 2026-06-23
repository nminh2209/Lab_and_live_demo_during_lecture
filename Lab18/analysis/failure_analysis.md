# Failure Analysis — Lab 18: Production RAG

**Nhóm:** Production RAG Batch 2  
**Thành viên:** M1 Chunking · M2 Search · M3 Rerank · M4 Eval · M5 Enrichment

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ |
|--------|---------------|------------|---|
| Faithfulness | 0.8167 | 0.7250 | -0.0917 |
| Answer Relevancy | 0.7203 | 0.7209 | +0.0007 |
| Context Precision | 0.9250 | 0.8875 | -0.0375 |
| Context Recall | 0.9250 | 0.7917 | -0.1333 |

**Nhận xét:** Production pipeline cải thiện nhẹ answer relevancy nhưng **context recall giảm 13%** so với baseline. Nguyên nhân chính: hierarchical child chunks (256 chars) + enrichment làm mất ngữ cảnh so với paragraph chunks lớn hơn của baseline; một số câu hỏi multi-hop/negation không retrieve đủ chunk liên quan.

---

## Bottom-5 Failures

### #1 — Phân loại dữ liệu lương (score: 0.33)

- **Question:** Thông tin lương thuộc cấp độ phân loại dữ liệu nào?
- **Expected:** Dữ liệu Bí mật (cấp 3), mã hóa khi truyền, hạn chế truy cập need-to-know.
- **Got:** Không tìm thấy.
- **Worst metric:** faithfulness (0.0)
- **Error Tree:** Output sai → Context đúng? **Không** (recall 0.5) → Query OK? Có → Root cause: **Retrieval miss** — chunk về `phan_loai_du_lieu.md` và `bang_luong_2024.md` không vào top-3 sau rerank.
- **Suggested fix:** Thêm metadata filter theo category (`compliance`, `salary`); tăng `HYBRID_TOP_K` trước rerank; dùng parent chunk thay vì child khi trả context.

### #2 — Nghỉ phép thử việc (score: 0.46)

- **Question:** Nhân viên thử việc có được nghỉ phép năm không?
- **Expected:** KHÔNG — phải xin nghỉ không lương.
- **Got:** Không tìm thấy.
- **Worst metric:** faithfulness (0.0)
- **Error Tree:** Output sai → Context đúng? **Có** (recall 1.0) → Query OK? Có → Root cause: **Generation failure** — LLM trả "Không tìm thấy" dù context đã có thông tin trong `thu_viec.md`.
- **Suggested fix:** Cải thiện prompt: yêu cầu trả lời CÓ/KHÔNG rõ ràng; hạ temperature; thêm few-shot cho câu hỏi negation.

### #3 — Mua thiết bị 55 triệu (score: 0.53)

- **Question:** Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt?
- **Expected:** Tổng Giám đốc (CEO) — đơn hàng trên 50 triệu.
- **Got:** Cần thêm phê duyệt của Kế toán trưởng.
- **Worst metric:** context_recall (0.0)
- **Error Tree:** Output sai → Context đúng? **Không** → Query OK? Có → Root cause: **Missing chunk** — ngưỡng phê duyệt CEO (>50M) trong `mua_sam.md` không được retrieve; model hallucinate từ chunk kế toán.
- **Suggested fix:** Structure-aware chunking giữ nguyên bảng ngưỡng phê duyệt; BM25 tốt hơn cho số liệu cụ thể ("55 triệu", "50.000.000").

### #4 — Tạm ứng quá hạn (score: 0.67)

- **Question:** Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu?
- **Expected:** Pro-rata ~50.000 VNĐ cho 5 ngày quá hạn (2%/tháng trên 15M).
- **Got:** 300.000 VNĐ (tính full 1 tháng thay vì pro-rata).
- **Worst metric:** faithfulness (0.33)
- **Error Tree:** Output sai → Context đúng? **Một phần** (recall 0.5) → Query OK? Có → Root cause: **LLM reasoning error** — context có quy tắc 2%/tháng nhưng thiếu ví dụ pro-rata; model làm tròn thành 1 tháng.
- **Suggested fix:** Enrichment thêm worked examples cho numeric questions; prompt yêu cầu tính pro-rata khi có số ngày quá hạn.

### #5 — Lương thử việc Junior (score: 0.71)

- **Question:** Lương thử việc của nhân viên Junior mức cao nhất là bao nhiêu?
- **Expected:** 17.000.000 VNĐ/tháng (= 85% × 20M ceiling).
- **Got:** 17.000.000 VNĐ (đúng số nhưng RAGAS faithfulness = 0).
- **Worst metric:** faithfulness (0.0)
- **Error Tree:** Output sai (theo RAGAS) → Context đúng? **Có** (recall 1.0) → Query OK? Có → Root cause: **Answer format mismatch** — câu trả lời đúng con số nhưng thiếu giải thích 85%×20M; RAGAS penalize vì không khớp ground truth đầy đủ.
- **Suggested fix:** Prompt yêu cầu trả lời kèm công thức tính; hoặc dùng structured output (số + giải thích).

---

## Case Study (cho presentation)

**Question chọn phân tích:** Nhân viên thử việc có được nghỉ phép năm không?

**Error Tree walkthrough:**

1. **Output đúng?** → Không — trả "Không tìm thấy" thay vì "KHÔNG".
2. **Context đúng?** → Có — `context_recall = 1.0`, chunk `thu_viec.md` đã được retrieve.
3. **Query rewrite OK?** → Có — hybrid search tìm đúng tài liệu thử việc.
4. **Fix ở bước:** Generation (M4 prompt) — không phải retrieval. Prompt hiện tại quá bảo thủ: "Nếu không có → nói Không tìm thấy" khiến model bỏ qua thông tin phủ định trong context.

**Nếu có thêm 1 giờ, sẽ optimize:**

- Sửa system prompt: "Trả lời CÓ hoặc KHÔNG rõ ràng nếu context có thông tin liên quan"
- Giảm child chunk size hoặc return parent context sau rerank
- Thêm version metadata filter để ưu tiên policy v2024/v2.0
- Chạy lại RAGAS và so sánh faithfulness trên nhóm câu negation
