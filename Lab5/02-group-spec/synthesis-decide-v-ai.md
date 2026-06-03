# Synthesis & Decide — V-App / V-AI

Toolkit hoàn thành — từ evidence đến build slice Day 06.

---

## 1. Gom evidence thành cụm

Gom theo **workflow/pain**, không theo tên feature.

| Cụm pain | Evidence |
|---|---|
| **"Đọc xong vẫn không làm được trong app"** | Happy path chỉ bullet + tag; không deep-link; dẫn Long Châu khi hỏi in-app |
| **"Cần hủy / trừ tiền / khiếu nại — kẹt"** | Chỉ text hotline/email; không Gọi/Chat/Ticket |
| **"Không tin câu trả lời — nguồn ở đâu?"** | Tag không click; AI hallucinate giải thích backtick |
| **"AI hiểu sai — sửa được nhưng vẫn một mình"** | Correction re-intent OK; không auto handoff sau 2 lần |
| **"Link/webview chết"** | RAG mở URL ngoài → blank screen |

**Cụm chọn build Day 06:** *"Cần hủy / trừ tiền / khiếu nại — kẹt"* (+ liên quan deep-link cho flow hủy)

---

## 2. Viết insight

```text
User V-App (đã có giao dịch / đăng ký dịch vụ VinGroup) không chỉ cần câu trả lời tra cứu.
Họ thật ra cần hoàn tất hành động hoặc được chuyển người ngay khi việc nhạy cảm (tiền, hủy dịch vụ),
vì self-use cho thấy V-AI dừng ở text hướng dẫn + hotline — user phải thoát app tự xử lý.
```

```text
User V-App không chỉ cần "biết các bước hủy thanh toán tự động".
Họ cần một lối thoát có nút bấm (deep-link hoặc CSKH) tại đúng moment frustration,
vì correction path chứng minh AI có thể hiểu đúng intent sau khi user sửa — nhưng không escalate.
```

---

## 3. Viết opportunity

```text
Cơ hội là dùng AI để phân loại intent (tra cứu / mơ hồ / nhạy cảm) và route response,
giúp user hoặc mở đúng màn hình V-App (deep-link) hoặc kết nối CSKH một chạm,
trong khi vẫn kiểm soát rủi ro bằng auto-handoff khi fallback ≥ 2 hoặc intent tài chính.
```

---

## 4. Chọn build slice

| Câu hỏi | Đạt? | Ghi chú |
|---|---|---|
| User cụ thể chưa? | ✅ | User V-App đang dùng dịch vụ VinGroup, cần hủy TT tự động hoặc hỏi về khoản trừ |
| Task đủ hẹp chưa? | ✅ | 1 flow: hỏi hủy TT tự động → AI classify → CTA deep-link + handoff |
| AI decision rõ chưa? | ✅ | AI quyết: `lookup` \| `clarify` \| `sensitive_handoff` |
| Failure path rõ chưa? | ✅ | AI chỉ text hotline, không CTA — user kẹt |
| Có evidence không? | ✅ | Self-use + individual teardown; review store bổ sung M1 |

**Build slice chốt:**

```text
Cho user V-App đang muốn hủy thanh toán tự động (hoặc hỏi về khoản trừ / khiếu nại),
prototype dùng AI để phân loại intent nhạy cảm và đưa [Đến màn hình hủy] + [Gọi CSKH] + [Chat],
tạo ra actionable next step trong chat,
và xử lý failure (AI chỉ trả text hotline) bằng bắt buộc hiển thị CTA + auto-handoff sau 2 lần "Không đúng".
```

---

## 5. Quyết định: giữ, giảm scope, hay đổi hướng?

| Tình huống | Quyết định nhóm |
|---|---|
| Evidence yếu, user mơ hồ | **Giữ** — self-use đủ mạnh; bổ sung review store sáng Day 06 |
| Ý tưởng quá rộng | **Giảm scope** — bỏ full RAG, clickable source, webview fix → backlog |
| AI không cần thiết | **Không** — intent classify là core; response có thể rule/template |
| Rủi ro cao | **Conditional automation** — sensitive → handoff ngay |
| Không demo được trong 1 ngày | **Backlog** (mục 7) — chỉ giữ 1 path demo |

---

## 6. Câu chốt cuối

```text
Dựa trên self-use V-AI (happy tra cứu + handoff text-only + correction re-intent),
nhóm sẽ build prototype chat mock "V-AI Handoff Router",
cho user V-App cần hủy thanh toán tự động / hỏi trừ tiền,
để giải quyết pain "đọc xong vẫn phải thoát app tự gọi/email",
bằng cách AI phân loại intent và route deep-link + CSKH CTA,
và sẽ test failure path "AI chỉ trả text 1900/email không có nút".
```

---

## 7. Backlog (không build Day 06)

- Clickable source tags + bottom sheet minh bạch nguồn
- Sửa hallucination giải thích nguồn (metadata-driven only)
- Webview blank recovery cho link RAG ngoài VinGroup
- Quick reply chips cho low-confidence (thay text `->`)
- False_Positive_Logs pipeline cho correction
- Full in-app nhắc thuốc / Long Châu routing fix

---

*Synthesis · V-App V-AI · Batch 02 Day 05*
