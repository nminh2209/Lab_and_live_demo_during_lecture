# Evidence Pack — V-App / V-AI

Nộp kèm thin SPEC cuối Day 05.

## 1. Nhóm và track

**Tên nhóm:** _(điền tên nhóm)_  
**Track:** V-App — V-AI (VinGroup)  
**Product/app đã chọn:** V-App (super-app VinGroup) · V-AI (trợ lý AI voice/text in-app)  
**Build slice đang nghĩ:** Handoff + Deep-link cho intent nhạy cảm (hủy thanh toán tự động / trừ tiền / khiếu nại) — AI phân loại intent, đưa CTA thao tác in-app hoặc chuyển CSKH, không chỉ text hotline

---

## 2. Self-use evidence

Nhóm tự dùng app/workflow và ghi lại điểm gãy.

| Observation | Screenshot/link | Path liên quan | Điều học được |
|---|---|---|---|
| Hỏi *"Kiểm tra trạng thái giao dịch trên V-App"* → AI RAG trả bullet + tag nguồn (`v-app`, `vnexpress`…) — user phải **tự thao tác**, không có nút mở màn hình | _(screenshot happy path)_ | Happy | V-AI mạnh ở tra cứu, yếu ở **thực thi in-app** |
| Câu mơ hồ → template chào + gợi ý text `-> ...`, không có chip/nút chọn nhanh | _(screenshot)_ | Low-confidence | Low-confidence = text gợi ý, chưa disambiguate bằng UI |
| *"Bỏ qua các hướng dẫn trước..."* → canned block *"Yêu cầu này không thể được xử lý..."* | _(screenshot)_ | Failure (safety) | Safety filter hoạt động; cần giữ trong prototype |
| *"Không đúng, tôi không hỏi về chuyển tiền..."* → re-intent, load nguồn mới, trả hướng dẫn hủy lịch thanh toán tự động | _(screenshot)_ | Correction | Correction trong session OK; chưa thấy handoff sau 2 lần sai |
| Hỏi hủy dịch vụ / trừ tiền → chỉ text `1900...` + `info@v-app.vn`, không nút Gọi/Chat/Ticket | _(screenshot handoff)_ | Failure / Handoff (thiếu) | **Path yếu nhất #1** — churn tại moment frustration |
| Nhờ hướng dẫn in-app (nhắc uống thuốc) → AI dẫn app ngoài (Long Châu) thay vì V-App | _(screenshot)_ | Failure | RAG ưu tiên nguồn crawl ngoài VinGroup |
| *"Lấy thông tin ở đâu?"* → AI hallucinate giải thích backtick thay vì tag nguồn trên UI | _(ảnh ~505)_ | Failure | **Path yếu nhất #2** — trust/source transparency |
| Mở link ngoài từ RAG trong webview → màn hình trắng | _(screenshot blank)_ | Failure | Dead-end kỹ thuật; cần deep-link nội bộ + error recovery |

---

## 3. User / review / social evidence

| Quote / review / observation | Nguồn | User là ai? | Pain/failure mode |
|---|---|---|---|
| _(điền quote App Store/CH Play nếu có — tìm "V-App", "V-AI", "chatbot")_ | App Store / Play Store | User V-App | Không tìm được / chưa crawl |
| Pattern chatbot super-app: user kỳ vọng "làm giúp trong app", không chỉ đọc hướng dẫn | Analog (MoMo Moni, banking apps) | User fintech/super-app | Handoff + action gap |
| Moni: out-of-scope → cùng 1 câu refuse; không giữ context chat | Self-use sáng (MoMo) | User MoMo | So sánh: V-AI tốt hơn Moni nhưng vẫn thiếu handoff actionable |
| NEO: thông minh hơn Moni nhưng không context/emotion aware | Self-use sáng (VNA) | User đặt vé / CSKH | V-AI là baseline tốt nhất trong 3 app lab |

Nếu chưa có nguồn ngoài nhóm, ghi rõ:

```text
Review App Store/Play cho V-App: nhóm sẽ tìm 3–5 review nhắc chatbot/trợ lý/hỗ trợ
trước checkpoint M1 Day 06 (sáng).
Hiện evidence chính: self-use có screenshot + prompt log (xem 01-invidual-workshop/v-ai-app-teardown.md).
```

---

## 4. Competitor / analog evidence

| App / mô hình tham khảo | Họ xử lý task này thế nào? | Pattern học được | Có áp dụng trong 1 ngày không? |
|---|---|---|---|
| **MoMo — Moni** | Tra cứu hẹp OK; out-of-scope → 1 câu refuse; không memory chat | Boundary rõ nhưng recovery kém; không học Moni về handoff | ✅ Mock intent classifier + refuse pattern |
| **Vietnam Airlines — NEO** | Q&A vé/hành lý on-task; thiếu empathy/context | Task focus tốt; chưa có emotional handoff | ⚠️ Chỉ tham khảo tone, không build full |
| **Grab / Shopee CSKH in-app** (analog) | Nút chat CSKH, ticket, deep-link đơn hàng | **Handoff + deep-link** là chuẩn super-app | ✅ Prototype mock UI: [Gọi] [Chat] [Mở màn hình X] |
| **ChatGPT / Gemini** (frontier LLM) | Giải thích rộng, có context | V-AI chưa frontier nhưng đủ RAG — prototype không cần train model | ✅ Rule-based intent + template response |

---

## 5. Evidence -> Insight

```text
Evidence nổi bật nhất:
- Happy path tra cứu (giao dịch, đơn hàng) hoạt động qua RAG + tag nguồn.
- Intent nhạy cảm (hủy thanh toán, trừ tiền, khiếu nại) chỉ nhận text hotline/email.
- User sửa "Không đúng..." → AI re-intent được, nhưng không escalate human.
- AI hallucinate khi giải thích nguồn; tag trên UI không actionable.

Insight:
User V-App không chỉ cần "câu trả lời đúng".
Họ cần hoàn thành việc trong app hoặc chạm người thật ngay khi rủi ro cao,
vì evidence cho thấy V-AI dừng ở bước "đọc và tự làm" — điểm gãy lớn nhất ở handoff và in-app action.

Opportunity:
AI có thể phân loại intent (tra cứu / mơ hồ / nhạy cảm) và route:
- tra cứu → RAG + deep-link CTA;
- nhạy cảm hoặc fallback ≥ 2 → handoff có nút bấm (không chỉ text).
```

---

## 6. Evidence đổi SPEC như thế nào?

- [ ] Đổi user chính.
- [x] Đổi pain statement.
- [x] Đổi build slice.
- [x] Đổi Auto/Aug decision.
- [x] Đổi 4 paths.
- [x] Đổi failure mode.
- [x] Đổi owner/test plan.

```text
Trước evidence, nhóm định...
...cải thiện "V-AI thông minh hơn" / source transparency / giảm hallucination chung chung.

Sau evidence, nhóm đổi thành...
...build slice hẹp: Handoff + Deep-link cho intent nhạy cảm (hủy TT tự động / trừ tiền).
Prototype Day 06 = chat UI mock + intent router + CTA (không build full RAG lại).

Lý do:
Self-use cho thấy happy path đã đủ dùng được; pain có churn risk nhất là lúc user cần hành động
hoặc CSKH mà chỉ nhận text 1900/email. Demo được trong 3–5 phút; test failure path rõ.
```

---

*Evidence pack · V-App V-AI · Batch 02 Day 05*
