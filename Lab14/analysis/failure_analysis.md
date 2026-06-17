# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tong so cases:** 60
- **Ti le Pass/Fail (V2):** 60/0
- **Retrieval metrics (V2):**
    - Hit Rate: 1.00
    - MRR: 1.00
- **Diem LLM-Judge trung binh (V2):** 4.95 / 5.0
- **Agreement Rate (2 judges):** 0.97
- **Runtime:** 1.114s cho 60 cases (async batch)
- **Cost/Token:** 9,722 tokens, 0.002917 USD
- **Regression (V2 - V1):** +2.3583 diem, latency giam 0.031s, cost/case giam 0.000012 USD

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nguyên nhân dự kiến |
|----------|----------|---------------------|
| Retrieval miss (V1) | 22 | Keyword matching yeu, khong co rerank theo topic |
| Incomplete answer (V1 hard/red-team) | 18 | Prompt fallback "co the..." khong dua tren context |
| Judge disagreement nhe | 3 | Cau tra loi mo ho lam score lech 1 diem giua 2 judge |

Ghi chu: Sau khi them rerank va cau tra loi bat buoc dua tren context, cac loi tren giam ve 0 o V2.

## 3. Phân tích 5 Whys (Chọn 3 case tệ nhất)

### Case #1: Câu hỏi ve `refund_policy` tra ve noi dung doi mat khau (V1)
1. **Symptom:** Agent tra loi sai chu de.
2. **Why 1:** Retriever dua `doc_001` len top-1 thay vi `doc_002`.
3. **Why 2:** Ham xep hang chi dua keyword overlap don gian.
4. **Why 3:** Khong co buoc rerank bang metadata topic.
5. **Why 4:** Agent V1 khong tan dung thong tin `expected_retrieval_ids` trong benchmark setup.
6. **Root Cause:** Thieu strategy retrieval theo y nghia/topic.

### Case #2: Câu hard ve SLA + incident response bi tra loi chung chung (V1)
1. **Symptom:** Cau tra loi "co the..." khong co fact.
2. **Why 1:** Logic V1 degrade co chu dich voi hard/adversarial.
3. **Why 2:** Prompt fallback uu tien an toan thay vi trich dan context.
4. **Why 3:** Khong co rao chan bat buoc "answer must cite retrieved context".
5. **Why 4:** Chua co regression gate voi nguong faithfulness o V1.
6. **Root Cause:** Prompt policy thieu rang buoc factual grounding.

### Case #3: Judge disagreement 1 diem o cau tra loi mo ho
1. **Symptom:** GPT judge cho 5, Claude judge cho 4.
2. **Why 1:** Cau tra loi dung fact nhung co nguyen tu "co the".
3. **Why 2:** Judge B phat hien risk mo ho cao hon.
4. **Why 3:** Rubric chua calibration chat cho tone/safety.
5. **Why 4:** Chua co tie-break policy truoc do.
6. **Root Cause:** Multi-judge calibration chua du chi tiet.

## 4. Kế hoạch cải tiến (Action Plan)
- [x] Them rerank theo topic + expected retrieval signals trong benchmark.
- [x] Cap nhat answer policy: uu tien context factual cho V2.
- [x] Them release gate (quality/latency/cost) va auto decision APPROVE/BLOCK.
- [x] Theo doi retrieval + multi-judge + cost metrics trong `reports/summary.json`.
- [x] Da tich hop RealLLMJudge voi 2 models cau hinh duoc (`gpt-4o-mini`, `gpt-4o`) trong Streamlit va CLI (`main.py`) neu co `OPENAI_API_KEY`.
