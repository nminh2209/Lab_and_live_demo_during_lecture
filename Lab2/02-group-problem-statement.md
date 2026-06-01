# 02 — Group Problem Statement

## Group convergence

| Cluster | Candidate examples | Pattern chung |
|---|---|---|
| Xử lý tài liệu hành chính | Trích xuất metadata dự thảo, review văn bản, format công văn | Đều tốn thời gian đọc hiểu và phải nhập liệu thủ công lại vào hệ thống |
| Quản lý dự án/Task | Báo cáo tuần, họp giao ban, theo dõi tiến độ | Tổng hợp dữ liệu từ nhiều nguồn (Jira, Sheets, Slack) |
| Tìm kiếm/FAQ | Tìm kiếm quyết định cũ, chatbot hỏi đáp nội quy | Mất thời gian tìm thông tin trong các kho lưu trữ rời rạc |

**Shortlist và score**

| Candidate | Actor rõ | Workflow rõ | Pain có evidence | Impact đo được | Làm trong lab | So sánh R/W/A được | Nhóm hiểu domain | Tổng |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Trích xuất metadata | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 35 |
| Báo cáo tuần | 4 | 5 | 4 | 4 | 4 | 4 | 4 | 29 |
| Tìm kiếm quyết định cũ | 3 | 3 | 4 | 3 | 3 | 4 | 3 | 23 |

**Nhóm chọn:** Trích xuất metadata từ văn bản dự thảo.

**Vì sao chọn:**
- Workflow cực kỳ rõ ràng, lặp lại hằng ngày với tần suất lớn.
- Có baseline thời gian dễ đo lường (5-10 phút/văn bản).
- Pain thật: nhập thủ công dễ sai sót, gây chậm tiến độ luân chuyển.
- AI (LLM) rất mạnh trong việc đọc hiểu và trích xuất thông tin có cấu trúc (JSON).

**Vì sao không chọn các bài khác:**
- Báo cáo tuần: Có nhiều cách giải quyết bằng Rule/Dashboard hơn là nhất thiết phải dùng AI.
- Tìm kiếm quyết định cũ: Scope về RAG (Retrieval-Augmented Generation) quá phức tạp và khó chuẩn bị data trong một buổi lab.

## Quick validation

Nhóm đã hỏi nhanh 3 chuyên viên văn thư/hành chính có kinh nghiệm xử lý văn bản:

| Nguồn | Số người | Tín hiệu xác nhận | Tín hiệu phản bác | Nhóm sửa problem thế nào |
|---|---:|---|---|---|
| Quick interview | 3 | 3/3 người xác nhận việc đọc và tự nhập trích yếu/nơi nhận rất mất thời gian và nhàm chán. | 1 người lo ngại về vấn đề bảo mật của văn bản dự thảo. | Giới hạn MVP: Chỉ áp dụng cho văn bản không mật, không đẩy dữ liệu nhạy cảm lên public cloud. |

**Insight sau validation:**
Pain không nằm ở thao tác upload file, mà nằm ở công đoạn nhận thức: phải tự đọc, tóm tắt ý chính và dò tìm danh sách nơi nhận bên trong file.

## Research giải pháp

| Nguồn / tool / case | Link | Họ giải quyết phần nào? | Điểm mạnh | Khoảng trống / rủi ro | Bài học cho nhóm |
|---|---|---|---|---|---|
| VNPT iOffice | https://vpdt.vnptioffice.vn/ | Hệ thống luân chuyển văn bản tổng thể. | Đã quen thuộc với quy trình nhà nước/doanh nghiệp. | Thường chưa có AI tự trích xuất thông tin nháp lúc mới upload. | Không làm lại cả hệ thống, chỉ định vị là một "bước Workflow" bổ sung khi upload. |
| Rossum IDP | https://rossum.ai/ | Tự động đọc và trích xuất dữ liệu tài liệu giao dịch. | Pattern tốt: AI extract → human validation. | Chưa được tối ưu cho ngôn ngữ và thể thức hành chính Việt Nam. | Thiết kế workflow bắt buộc có Human-in-the-loop để duyệt lại kết quả. |

**Research takeaway:**
Workflow nên đi theo hướng: Upload → AI Extract → Điền nháp vào form → Chuyên viên kiểm duyệt (Human boundary) → Xác nhận lưu.

## Workflow before/after

File nhóm nộp kèm: `02-group-problem-statement-workflow.md`

**CURRENT STATE — 6 bước, 5-10 phút**
```text
[1 Upload file dự thảo: 1']
→ [2 Đọc toàn bộ văn bản: 3-5']          <-- bottleneck
→ [3 Tự tóm tắt & nhập Trích yếu: 1-2']  <-- bottleneck
→ [4 Rà soát & nhập Nơi nhận: 1-2']
→ [5 Chọn Thể loại văn bản: 1']
→ [6 Bấm Lưu & Luân chuyển: 1']
```

**FUTURE STATE — 4 bước, dưới 2 phút**
```text
[1 Upload file dự thảo: 1']             -- Rule
→ [2 AI đọc & trích xuất JSON: 1']      -- Workflow step
→ [3 Chuyên viên rà soát, sửa: 1']      -- Human boundary
→ [4 Bấm Xác nhận & Luân chuyển: 1']
```

**Before/after impact:**

| Metric | Trước | Sau kỳ vọng | Ghi chú |
|---|---:|---:|---|
| Tổng thời gian xử lý | 5-10 phút/văn bản | Dưới 2 phút | Mục tiêu chính |
| Số bước thủ công | 6 | 3 | Chuyên viên chuyển từ "nhập liệu" sang "kiểm duyệt" |
| Bottleneck chính | Đọc hiểu & tự tóm tắt | Rà soát gợi ý của AI | Chấp nhận được vì đảm bảo chất lượng |
| Rủi ro mới | Không có AI hallucination | Automation bias (quá tin AI) | Cần thiết kế UI bắt buộc review |

## Problem Statement v0

| Field | Nội dung |
|---|---|
| **Actor** | Chuyên viên văn thư, chuyên viên hành chính phụ trách upload văn bản. |
| **Workflow** | Upload file dự thảo → Đọc toàn bộ văn bản → Tự tóm tắt trích yếu → Tự dò tìm và nhập nơi nhận → Chọn thể loại văn bản → Lưu. |
| **Bottleneck** | Bước đọc hiểu, tóm tắt và tự nhập lại metadata (Trích yếu, Nơi nhận) thủ công rất tốn thời gian và dễ sót ý khi file dài. |
| **Impact** | Tốn 5-10 phút/văn bản. Tốc độ luân chuyển hồ sơ chậm lại khi có hàng chục văn bản cần xử lý mỗi ngày. |
| **Success Metric** | Giảm thời gian điền form xuống dưới 2 phút/văn bản. Tỷ lệ chuyên viên chấp nhận gợi ý (hoặc chỉ sửa nhẹ) > 85%. |
| **Boundary** | AI chỉ được tạo bản nháp (draft), không tự động lưu/phê duyệt văn bản. Không áp dụng cho tài liệu mật. |

## Rule / Workflow / Agent

| Mức | Phương án | Khi nào đủ | Rủi ro | Chọn? |
|---|---|---|---|---|
| **Rule** | Dùng Regex hoặc Template để bóc tách các dòng cố định (như "Kính gửi", "Nơi nhận"). | Khi format văn bản tuân thủ 100% biểu mẫu cứng. | Dễ vỡ nếu format lệch, và không thể "tóm tắt" nội dung thành Trích yếu. | Không |
| **Workflow** | Upload file → gọi AI (LLM) extract JSON → fill form → người dùng kiểm tra → Lưu. | Khi quy trình rõ ràng, tuyến tính và AI giải quyết đúng 1 bước NLP. | AI trích xuất sai hoặc tóm tắt nhạt, cần người kiểm tra. | Chọn |
| **Agent** | AI tự quét thư mục, tự đọc văn bản, tự gửi lên hệ thống và tự tag tên người liên quan. | Khi quy trình có quá nhiều nhánh, cần AI tự lập kế hoạch. | Rủi ro sai sót rất lớn, vi phạm quyền phê duyệt, khó xin phép bảo mật. | Không |

**Mức chọn:** Workflow.

**Vì sao:**
- Quy trình đã có sẵn đường đi cố định từ đầu đến cuối.
- Khâu lấy dữ liệu khó (đọc hiểu) cần đến AI (LLM).
- Không cần AI tự quyết định làm gì tiếp theo, vì quy trình hành chính yêu cầu con người phê duyệt cuối cùng.

## Problem Statement v1

| Field | Nội dung |
|---|---|
| **Actor** | Chuyên viên văn thư, hành chính. |
| **Workflow** | Upload file → AI trích xuất metadata → Chuyên viên rà soát (sửa nếu cần) → Xác nhận lưu. |
| **Bottleneck** | Đọc hiểu và tóm tắt văn bản thô thành metadata cấu trúc. |
| **Impact** | Mỗi văn bản chiếm 5-10 phút thời gian chết, gây ùn tắc luân chuyển văn bản. |
| **Success Metric** | Dưới 2 phút xử lý form/văn bản. Acceptance rate của AI > 85%. |
| **Boundary** | AI chỉ đóng vai trò trợ lý nhập liệu nháp. Chỉ xử lý văn bản không mật. |
| **AI intervention point** | Ngay sau khi upload file, trước khi form nhập liệu hiện ra cho chuyên viên. |
| **Mức chọn** | Workflow: Rule (check file format) → AI (trích xuất text thành JSON) → Human (review). |
| **Rủi ro & người thật kiểm tra** | Rủi ro (Automation bias) - người dùng lười rà soát. Giải quyết: Giao diện bắt buộc chuyên viên phải lướt qua các trường và bấm "Xác nhận". |

## Final decision

**Decision:** Go với scope nhỏ.

**Pilot nhỏ nhất:**
- Tập dữ liệu: 10-20 file văn bản (.docx, .pdf text) không mật.
- Cách test: Thiết kế một prompt chuẩn trên ChatGPT hoặc script gọi API đơn giản, paste text của file vào và xem AI trả về JSON (Thể loại, Trích yếu, Nơi nhận) có chính xác và tiết kiệm thời gian hơn gõ tay không.

**Exit / rollback:**
- Nếu tỷ lệ AI trích xuất sai/thiếu nghiêm trọng quá 30% (người dùng phải gõ lại hoàn toàn), tạm dừng tích hợp AI và quay về dùng Template/Checklist truyền thống.

**Decision rationale:**
- Bài toán có workflow và điểm thắt nút rõ ràng.
- Rủi ro có thể kiểm soát hoàn toàn thông qua Human-in-the-loop (chuyên viên kiểm duyệt cuối).
- Baseline thời gian dễ đo lường, dễ chứng minh được giá trị cải thiện ngay lập tức.
