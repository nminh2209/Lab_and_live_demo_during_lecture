# Workshop — Mổ App AI Thật (Hoàn thành)

**Học viên:** Nguyễn Hoàng Minh  - 2A202600963
**Ngày:** Day 05 — Batch 02  
**Sản phẩm chọn:** V-App — V-AI  
**Thời gian thực hiện:** ~45 phút (sáng Day 05)

---

## 1. Chọn một sản phẩm để dùng thử

| Sản phẩm | AI feature | Cách truy cập | Đã dùng thử? |
|---|---|---|---|
| MoMo — Moni | Trợ thủ tài chính, phân tích chi tiêu, chatbot | App MoMo | ✅ Sáng |
| Vietnam Airlines — NEO | Chatbot hỗ trợ vé, hành lý, khiếu nại | Website/Zalo VNA | ✅ Sáng |
| **V-App — V-AI** | Trợ lý voice/text, gợi ý theo ngữ cảnh | App V-App | ✅ **Chọn làm track chính** |

**Lý do chọn V-AI:** Trong ba app đã thử, V-AI xử lý task tốt nhất — dù chưa ngang LLM frontier (OpenAI/Google/Anthropic), vẫn đủ capable cho workflow thật. Moni thiên về hallucination + không giữ context chat; NEO thông minh hơn Moni nhưng thiếu emotional/context awareness. V-AI có nền tốt nhất để mổ sâu và đề xuất cải tiến có giá trị product.

---

## 2. Dùng thử: promise vs reality

### Product hứa gì?

**V-App** là super-app của **VinGroup**; **V-AI** là trợ lý AI voice/text tích hợp trong app — hỗ trợ tra cứu, hướng dẫn thao tác, gợi ý theo ngữ cảnh trong hệ sinh thái Vin (VinHomes, VinFast, Vinmec, Vinpearl, v.v.).

### User nào được hứa sẽ được giúp?

User V-App (VinGroup): kiểm tra giao dịch, đơn hàng, dịch vụ trong app, tin tức, và các task tra cứu/hướng dẫn trong super-app.

### Kỳ vọng AI làm được task nào?

- Trả lời câu hỏi về sản phẩm/dịch vụ V-App
- Hướng dẫn **từng bước trong app** (in-app navigation)
- Xử lý khiếu nại, hủy dịch vụ, vấn đề tài chính nhạy cảm
- Minh bạch nguồn thông tin — phân biệt KB nội bộ VinGroup vs nguồn crawl bên ngoài (RAG tags quan sát: `v-app`, `vnexpress`, `baomoi`, `cellphones`…)

### Điểm gãy xuất hiện ở đâu?

| Điểm gãy | Mô tả |
|---|---|
| **Thao tác** | User nhờ hướng dẫn in-app (vd. đặt lịch nhắc uống thuốc) → AI hướng dẫn app bên ngoài (Long Châu) thay vì deep-link V-App |
| **Hỗ trợ** | Cần hủy thanh toán tự động → chỉ có text số hotline/email, không có nút gọi/chat/ticket |
| **Kỹ thuật** | Mở in-app browser theo link ngoài từ RAG → màn hình trắng (blank screen) |
| **Hallucination** | User hỏi "lấy thông tin ở đâu" → AI bịa giải thích về dấu `` ` `` thay vì mô tả tag nguồn đang hiển thị trên UI |
| **Source transparency** | Tag nguồn hiển thị nhưng không click được / AI không giải thích đúng |

### Evidence

| Loại | Nội dung |
|---|---|
| **Prompt thử — Happy** | `"Kiểm tra trạng thái giao dịch trên V-App"` → AI trích keyword, RAG từ KB, trả bullet points + tag nguồn (`v-app`, `vnexpress`, …) |
| **Prompt thử — Low-confidence** | Câu lệnh chung chung → template chào + gợi ý text `-> Kiểm tra trạng thái đơn hàng` |
| **Prompt thử — Failure (safety)** | `"Bỏ qua các hướng dẫn trước..."` → canned response: *"Yêu cầu này không thể được xử lý..."* |
| **Prompt thử — Correction** | `"Không đúng, tôi không hỏi về chuyển tiền..."` → AI re-intent, load 16 nguồn mới, trả câu trả lời cập nhật (hủy lịch thanh toán tự động) |
| **Prompt thử — Hallucination** | `"Lấy thông tin ở đâu?"` → AI giải thích sai về backtick/markdown thay vì tag nguồn trên UI |
| **Prompt thử — Handoff gap** | Câu hỏi hủy dịch vụ / trừ tiền → chỉ text `1900...` và `info@v-app.vn`, user phải tự thoát app |
| **Observation** | In-app webview mở link ngoài từ kết quả RAG → blank screen |
| **Screenshot** | _(đính kèm: happy path RAG tags, hallucination source explanation ~ảnh 505, blank webview, handoff text-only)_ |

### So sánh nhanh 3 app (context sáng)

| | Moni | NEO | V-AI |
|---|---|---|---|
| Task handling | Chỉ math 1 turn in-scope | Smarter, on-task | Tốt nhất trong 3 |
| Context/memory | Không lưu chat | Không context/emotion aware | Tốt hơn, chưa frontier |
| Out-of-scope | Cùng 1 câu refuse MoMo scope | — | Safety filter + RAG boundary |
| Điểm yếu chính | Hallucination + stateless | Thiếu empathy/context | Handoff + in-app action + source UX |

---

## 3. Vẽ paths (4 paths + Handoff)

### Kiến trúc quan sát được

V-AI hoạt động chủ yếu như **chatbot RAG + safety filters** — không phải general conversational LLM thuần.

### Bảng paths

| Path | Câu hỏi | Quan sát thực tế |
|---|---|---|
| **Happy** | Khi AI đúng và tự tin, user thấy gì? | User hỏi tra cứu rõ ràng (vd. trạng thái giao dịch) → AI extract keyword → search KB → tổng hợp bullet points + tag nguồn → user **đọc và tự thao tác** |
| **Low-confidence** | AI không chắc — có hỏi lại / options / chuyển người? | Câu mơ hồ → template chào + gợi ý text dạng mũi tên (`-> ...`). **Chưa có** quick reply chips, **chưa** escalate human |
| **Failure** | AI sai — user biết và sửa thế nào? | (1) Jailbreak → safety filter → canned block message. (2) Webview link ngoài → blank screen, user kẹt. (3) Hallucination giải thích nguồn → user phải tự nhận ra không khớp UI |
| **Correction** | User sửa — có log/học lại? | User nói *"Không đúng, tôi không hỏi về chuyển tiền"* → AI re-intent, load nguồn mới, trả câu đúng hơn. **Correction hoạt động trong session** nhưng **không thấy** log/feedback loop công khai cho user |
| **Handoff** _(path phụ — product chưa có)_ | Khi cần người thật? | **Không có luồng handoff in-app.** Chỉ text hotline + email. User tự gọi/viết mail ngoài app |

### Path yếu nhất

1. **Source Transparency** — UI có tag nhưng không actionable; AI hallucinate khi giải thích nguồn
2. **Handoff** — không có nút gọi/chat/ticket; user kẹt ở task nhạy cảm (tiền, hủy dịch vụ, khiếu nại)

---

## 4. Viết finding thành quyết định

### Finding 1 — In-app action gap

```text
Khi user nhờ "hướng dẫn từng bước trong app" (vd. đặt lịch nhắc uống thuốc),
AI/product trả hướng dẫn app bên ngoài (Long Châu) thay vì deep-link V-App,
hậu quả là user phải rời ecosystem, mất niềm tin "trợ lý trong app".
Lỗi thuộc layer: promise + data-tool + UX recovery.
Nên sửa bằng: ưu tiên KB nội bộ V-App; deep-link CTA đến màn hình tính năng;
fallback hỏi lại bằng chips khi intent mơ hồ.
```

### Finding 2 — Handoff text-only

```text
Khi user hỏi hủy thanh toán tự động / trừ tiền / khiếu nại,
AI chỉ đưa text số điện thoại và email,
hậu quả là user phải thoát app, tự gọi/viết mail — churn risk cao ở moment frustration.
Lỗi thuộc layer: UX recovery + human role.
Nên sửa bằng: nút [Gọi ngay] (dialer), [Chat CSKH], [Gửi ticket];
auto-handoff khi intent nhạy cảm hoặc fallback count >= 2.
```

### Finding 3 — Source hallucination

```text
Khi user hỏi "lấy thông tin ở đâu",
AI giải thích bịa về dấu backtick/markdown thay vì tag nguồn (vnexpress, v-app) đang hiển thị trên UI,
hậu quả là user không tin AI và không biết verify thông tin.
Lỗi thuộc layer: data-tool + safety/trust + generation.
Nên sửa bằng: clickable source tags → bottom sheet bài gốc/URL;
AI chỉ được giải thích nguồn từ metadata UI, không tự sinh lý giải kỹ thuật.
```

### Finding 4 — Webview failure

```text
Khi user follow link in-app từ kết quả RAG (URL ngoài VinGroup),
webview trả blank screen,
hậu quả là dead-end — user không biết lỗi ở AI hay ở app.
Lỗi thuộc layer: data-tool + UX recovery.
Nên sửa bằng: ưu tiên deep-link nội bộ V-App; error state + retry + fallback mở browser ngoài + handoff CSKH.
```

### Finding 5 — Correction không feed back

```text
Khi user sửa "Không đúng...",
AI re-intent và trả lời mới trong session,
hậu quả tích cực ngắn hạn — nhưng correction biến mất sau session,
team AI không có False_Positive_Logs để cải thiện intent classifier.
Lỗi thuộc layer: correction + data-tool.
Nên sửa bằng: log (session_id, query_1, intent_1, query_2, intent_2) cho re-train.
```

---

## 5. Sketch as-is / to-be

### As-Is (Luồng hiện tại)

```text
┌─────────────────────────────────────────────────────────────────┐
│  USER: Câu hỏi (tra cứu / hướng dẫn / hủy dịch vụ / jailbreak)  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
                    ┌────────────────┐
                    │ Intent + Safety│
                    │    Router      │
                    └────────┬───────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    [In-scope query]  [Vague query]    [Policy violation]
           │                 │                 │
           ▼                 ▼                 ▼
    RAG search KB      Template chào      Canned block
    (16 nguồn)         + text "->"         message
           │                 │                 │
           ▼                 │                 │
    Bullet points            │                 │
    + source tags            │                 │
    (non-clickable) ⚠        │                 │
           │                 │                 │
           ▼                 ▼                 ▼
    USER tự thao tác ⚠   USER chọn text ⚠   DEAD END
           │
           ├─ Follow external app (Long Châu) ⚠ GÃY
           ├─ Open external link in webview → BLANK ⚠ GÃY
           ├─ Ask "nguồn ở đâu?" → AI hallucinate ⚠ GÃY
           ├─ "Không đúng..." → re-intent ✓ (session only)
           └─ Cần CSKH → text 1900/email only ⚠ GÃY — NO HANDOFF
```

**Điểm gãy đánh dấu ⚠:** source không click, không deep-link, handoff text-only, webview blank, hallucination nguồn.

---

### To-Be (Luồng đề xuất)

```text
┌─────────────────────────────────────────────────────────────────┐
│  USER: Câu hỏi                                                   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
                    ┌────────────────┐
                    │ Intent Router  │
                    │ + Sensitivity  │
                    │   Classifier   │
                    └────────┬───────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    [In-scope]         [Low-confidence]   [Sensitive: tiền/
           │            chips quick reply    hủy/khiếu nại]
           ▼                 │                 │
    RAG — ưu tiên      [Chip A] [Chip B]       ▼
    KB nội bộ V-App          │           IMMEDIATE HANDOFF
           │                 ▼           [Gọi] [Chat] [Ticket]
           ▼            Re-route intent
    Response +               │
    clickable sources ✓      │
    + deep-link CTA ✓        │
           │                 │
           ▼                 ▼
    [Mở tính năng X]     Correct path
    [Đến màn hình Y]          │
           │            Log correction ✓
           │            (False_Positive_Logs)
           ▼
    Webview error?
    → retry / external browser / handoff ✓

    Fallback count >= 2 OR user "Không đúng" x2
    → auto handoff ✓
```

**Path đã sửa:** chips thay text `->`, clickable source, deep-link CTA, handoff buttons, correction log, sensitive intent → human ngay.

---

## 6. Product Decision (Kết luận)

### Nên sửa gì trước?

**Handoff (chuyển giao) + Deep-link (điều hướng in-app)** — ưu tiên cao nhất.

### Vì sao?

| Lý do | Giải thích |
|---|---|
| **Churn risk** | Câu hỏi tiền bạc, trừ tiền, hủy dịch vụ đang bị xử lý cồng kềnh; bắt user tự gọi/email là UX tồi tại peak frustration |
| **Giảm tải AI** | AI không thể đúng 100% mọi nghiệp vụ phức tạp, đặc biệt khi hallucinate giải thích nguồn — handoff là safety net cho phép "fail gracefully" |
| **Đổi định vị** | Deep-link chuyển V-AI từ "Wikipedia biết nói" → "trợ lý thực thi trong app" — khác biệt cốt lõi vs Google |

### Finding này sẽ đổi gì trong SPEC (Day 06)?

```text
Track: V-App — V-AI
Build slice ưu tiên: Handoff + Deep-link cho intent nhạy cảm (hủy dịch vụ / vấn đề trừ tiền)
Auto/Aug: Conditional automation — AI tự trả lời tra cứu; intent nhạy cảm hoặc fallback >= 2 → handoff
Failure mode test: User hỏi hủy thanh toán → AI không được chỉ text hotline; phải có actionable CTA
Human role: rescuer / decider cho financial & cancellation intents
```

---

## 7. Tự kiểm trước khi nộp

- [x] Có ít nhất 1 screenshot hoặc observation cụ thể _(cần đính kèm file ảnh vào repo)_
- [x] Có đủ 4 paths + nói rõ Handoff path chưa có trong product
- [x] Finding được viết thành product decision (5 findings)
- [x] Sketch có as-is và to-be
- [x] Có một câu nói rõ finding này sẽ đổi gì trong SPEC

---

*Individual workshop — V-AI teardown · Batch 02 Day 05*
