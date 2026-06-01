# 03 — Individual Reflection
> Day 02 Lab — Nguyen Hoang Minh

---

## 1. Đóng góp của tôi (Giả định trong vai trò mô phỏng nhóm)

| Hoạt động | Tôi đã làm gì? | Kết quả / Ảnh hưởng |
|---|---|---|
| **Scan cá nhân** | Chủ động scan 10 problems, áp dụng góc nhìn cá nhân (ADHD) và trải nghiệm thực tế từ các project (HMU, BlueOC). | Cung cấp rất nhiều lựa chọn thực tế và đa dạng lăng kính để phân tích. |
| **Pitch & Chọn Problem** | Đề xuất bài toán "Morning Context Overload". | Bài toán được chọn vì có workflow cực kỳ tuyến tính và dễ đo lường thành công. |
| **Workflow** | Vẽ chi tiết các bước Current vs Future workflow, làm rõ bottleneck là bước "tự tổng hợp". | Xác định được chính xác vị trí AI cần nhảy vào (để Read & Draft) và điểm con người kiểm soát (Human boundary). |
| **So sánh R/W/A** | Loại bỏ Agent vì bài toán chỉ là gom thông tin một chiều, không cần AI phải tự quyết định làm thay con người. | Quyết định chọn "Workflow" an toàn, dễ triển khai pilot. |

---

## 2. Việc dùng AI trong quá trình làm Lab

| Phase | Tôi dùng AI để làm gì? | AI hữu ích ở đâu? | AI sai/hời hợt ở đâu? | Tôi sửa gì bằng nhận định của mình? |
|---|---|---|---|---|
| **Scan** | Tham khảo các ý tưởng về nỗi đau của developer để bổ sung góc nhìn. | Giúp gọi tên chính xác các thuật ngữ (như "context switching cost", "vague requirements"). | Đôi khi AI gợi ý các pain point quá vĩ mô (vd: "làm bot tự code"). | Tôi gạt bỏ các ý vĩ mô, chỉ giữ lại các vấn đề tôi thực sự trải nghiệm (như việc review PR, client im lặng). |
| **Problem Statement** | Dùng AI để review form PS xem các field đã đủ liên kết logic với nhau chưa. | Chỉ ra rằng metric lúc đầu của tôi hơi định tính. | Đề xuất tôi làm một con Agent tự trả lời mail cho nhanh. | Tôi bác bỏ ý tưởng Agent, giữ mức Workflow và nhấn mạnh boundary là "không cho AI tự gửi mail". |
| **Workflow** | Phân tách các bước vẽ flow trước/sau cho chuẩn. | Hỗ trợ cấu trúc rành mạch, tính toán thời gian tổng rất nhanh. | Gộp bước tóm tắt và bước review làm một. | Tôi tách hẳn bước AI tóm tắt và bước Developer duyệt thành 2 bước riêng biệt để đảm bảo Human Boundary. |

---

## 3. Bài học cá nhân rút ra sau Lab

1. **Problem first, AI second:** Không phải vấn đề nào cũng cần nhét một con AI thật to (Agent) vào. Đôi khi một đoạn script (Rule) để gom dữ liệu cộng với một bước gọi LLM (Workflow) để tóm tắt đã giải quyết được 80% nỗi đau rồi.
2. **Vai trò của Workflow & Bottleneck:** Vẽ workflow hiện tại là bước quan trọng nhất. Nếu không nhìn thấy được nút thắt cổ chai (bottleneck) đang nằm ở đâu và tốn bao nhiêu thời gian, thì mọi giải pháp AI đưa ra đều là "solution in search of a problem" (giải pháp đi tìm vấn đề).
3. **Giới hạn của AI (Boundary):** Đối với các vấn đề có rủi ro về thông tin cá nhân hoặc giao tiếp với sếp/client, thiết lập ranh giới (Human review) là yếu tố quyết định để dự án thực sự chạy được (Go) thay vì chỉ nằm trên giấy (Not Yet).

**Nếu làm lại:**
Tôi sẽ làm thêm một mini-survey nhỏ gửi cho các bạn developer khác trong lớp để lấy dữ liệu định lượng chính xác hơn về thời gian họ lãng phí cho việc "setup ngữ cảnh" mỗi sáng, thay vì chỉ ước lượng dựa trên bản thân. Mức độ thuyết phục của Problem Statement sẽ cao hơn rất nhiều.
