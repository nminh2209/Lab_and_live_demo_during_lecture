# Ngày 1 — Bài Tập & Phản Ánh
## Nền Tảng LLM API | Phiếu Thực Hành

**Thời lượng:** 1:30 giờ  
**Cấu trúc:** Lập trình cốt lõi (60 phút) → Bài tập mở rộng (30 phút)

---

## Phần 1 — Lập Trình Cốt Lõi (0:00–1:00)

Chạy các ví dụ trong Google Colab tại: https://colab.research.google.com/drive/172zCiXpLr1FEXMRCAbmZoqTrKiSkUERm?usp=sharing

Triển khai tất cả TODO trong `template.py`. Chạy `pytest tests/` để kiểm tra tiến độ.

**Điểm kiểm tra:** Sau khi hoàn thành 4 nhiệm vụ, chạy:
```bash
python template.py
```
Bạn sẽ thấy output so sánh phản hồi của GPT-4o và GPT-4o-mini.

---

## Phần 2 — Bài Tập Mở Rộng (1:00–1:30)

### Bài tập 2.1 — Độ Nhạy Của Temperature
Gọi `call_openai` với các giá trị temperature 0.0, 0.5, 1.0 và 1.5 sử dụng prompt **"Hãy kể cho tôi một sự thật thú vị về Việt Nam."**

**Bạn nhận thấy quy luật gì qua bốn phản hồi?** (2–3 câu)
> Khi temperature thấp (0.0), phản hồi thường rất trực tiếp, máy móc và ít biến đổi nếu chạy lại nhiều lần. Khi temperature tăng dần lên (0.5 - 1.5), mô hình trở nên sáng tạo hơn, sử dụng từ vựng phong phú và có thể đưa ra những sự thật bất ngờ, tuy nhiên ở mức rất cao (1.5) văn bản có thể trở nên lộn xộn hoặc mất tính logic.

**Bạn sẽ đặt temperature bao nhiêu cho chatbot hỗ trợ khách hàng, và tại sao?**
> Tôi sẽ đặt temperature ở mức thấp, khoảng 0.0 đến 0.3. Đối với chatbot hỗ trợ khách hàng, tính chính xác, nhất quán và rõ ràng quan trọng hơn sự sáng tạo, để đảm bảo khách hàng luôn nhận được cùng một câu trả lời chuẩn xác cho cùng một vấn đề.

---

### Bài tập 2.2 — Đánh Đổi Chi Phí
Xem xét kịch bản: 10.000 người dùng hoạt động mỗi ngày, mỗi người thực hiện 3 lần gọi API, mỗi lần trung bình ~350 token.

**Ước tính xem GPT-4o đắt hơn GPT-4o-mini bao nhiêu lần cho workload này:**
> Dựa trên chi phí ($0.010 cho GPT-4o và $0.0006 cho GPT-4o-mini trên 1000 output tokens), GPT-4o đắt hơn GPT-4o-mini khoảng 16.67 lần (0.010 / 0.0006).

**Mô tả một trường hợp mà chi phí cao hơn của GPT-4o là xứng đáng, và một trường hợp GPT-4o-mini là lựa chọn tốt hơn:**
> - **Trường hợp dùng GPT-4o:** Khi cần xử lý suy luận phức tạp, phân tích dữ liệu chuyên sâu, lập trình hoặc viết nội dung yêu cầu chất lượng rất cao (ví dụ: tư vấn luật, phân tích báo cáo tài chính).
> - **Trường hợp dùng GPT-4o-mini:** Khi xử lý các tác vụ đơn giản, lặp đi lặp lại với khối lượng lớn như phân loại văn bản, tóm tắt bài viết ngắn, hoặc các chatbot trả lời câu hỏi FAQ cơ bản.

---

### Bài tập 2.3 — Trải Nghiệm Người Dùng với Streaming
**Streaming quan trọng nhất trong trường hợp nào, và khi nào thì non-streaming lại phù hợp hơn?** (1 đoạn văn)
> Streaming đặc biệt quan trọng trong các ứng dụng chatbot tương tác (như ChatGPT), nơi người dùng muốn thấy phản hồi xuất hiện ngay lập tức thay vì phải chờ đợi nhiều giây cho một đoạn văn bản dài, giúp giảm cảm giác chờ đợi và tạo cảm giác tự nhiên như đang trò chuyện. Ngược lại, non-streaming phù hợp hơn cho các tác vụ xử lý hàng loạt (batch processing), tự động hóa backend (như phân tích hàng nghìn email, tóm tắt tài liệu), hoặc khi ứng dụng yêu cầu toàn bộ kết quả phải hoàn chỉnh để phân tích/lưu trữ (ví dụ trả về JSON có cấu trúc chặt chẽ).


## Danh Sách Kiểm Tra Nộp Bài
- [x] Tất cả tests pass: `pytest tests/ -v`
- [x] `call_openai` đã triển khai và kiểm thử
- [x] `call_openai_mini` đã triển khai và kiểm thử
- [x] `compare_models` đã triển khai và kiểm thử
- [x] `streaming_chatbot` đã triển khai và kiểm thử
- [x] `retry_with_backoff` đã triển khai và kiểm thử
- [x] `batch_compare` đã triển khai và kiểm thử
- [x] `format_comparison_table` đã triển khai và kiểm thử
- [x] `exercises.md` đã điền đầy đủ
- [x] Sao chép bài làm vào folder `solution` và đặt tên theo quy định 
