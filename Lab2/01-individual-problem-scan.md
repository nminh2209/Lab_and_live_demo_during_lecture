# 01 — Individual Problem Scan
> Day 02 Lab — Nguyen Hoang Minh

---

## Scan rộng

| # | Lăng kính | Problem quan sát được | Ai đang đau? | Dấu hiệu thật |
|---|---|---|---|---|
| 1 | Lặp lại | Mỗi sáng phải mở thủ công Gmail, work mail, Canvas, stocks, coding workspace — mỗi app riêng lẻ | Developer/student bắt đầu ngày làm việc | Lặp lại 7 ngày/tuần, mất 5-10 phút mỗi sáng chỉ để setup môi trường |
| 2 | Lặp lại + AI có thể tốt hơn | Đã tự build Python script auto-open workspace, nhưng chưa có context summarization — vẫn phải đọc từng tab để biết hôm nay cần làm gì | Bản thân — developer có ADHD | Script chạy nhưng vẫn tốn 10-15 phút đọc và tổng hợp để ra được task priority |
| 3 | Tốn thời gian + ADHD | Khi học theo tutorial, phải nhớ syntax cụ thể — dễ mất tập trung và bỏ dở | Developer ADHD học kỹ năng mới | Thường chuyển tab, mở YouTube, hoặc chuyển sang prompting AI thay vì hoàn thành bài |
| 4 | Pain từ người khác + tốn thời gian | Client/stakeholder feedback quá mơ hồ — "UX bad", "tôi không thích UI" — không có DoD rõ, developer không biết done nghĩa là gì, dẫn đến build sai hoặc build xong bị yêu cầu làm lại | Developer, tech lead, PM trong dự án có client không technical | HMU: chỉ gặp client 3-4 lần trong 7 tháng, 3 tháng cuối client im lặng hoàn toàn — team build dựa trên giả định, feature template bị xóa sau 2 tuần làm vì không có trong requirements. BlueOC: CEO feedback "UX bad / tôi không biết dùng" không chỉ ra điểm cụ thể, developer phải đoán và làm lại nhiều lần |
| 5 | Pain từ người khác | PR review tốn thời gian — phải ping tech lead nhiều lần, tech lead phải đọc hàng trăm dòng code, bottleneck cả team | Developer + tech lead trong team project | Thường mất 1-2 ngày để PR được review và approve, làm chặn tiến độ |
| 6 | Pain từ người khác | Merge conflict xảy ra thường xuyên khi nhiều người làm cùng branch hoặc cùng file | Cả team dev | Mỗi sprint có ít nhất 2-3 conflict cần resolve thủ công, mất 30-60 phút |
| 7 | Pain từ người khác | Communication trong team không đồng bộ — task bị hiểu khác nhau, hỏi lại lặp lại, không biết ai đang làm gì | Team member, PM, tech lead | Hay có tin nhắn hỏi "bạn đang làm task nào rồi?" hoặc "cái này merge chưa?" |
| 8 | Lặp lại + tốn thời gian | Viết PR description mỗi lần commit — phải tự tóm tắt những gì đã thay đổi, tại sao, và impact là gì | Developer | Lặp lại mỗi PR, thường viết qua loa vì tốn thời gian, dẫn đến reviewer không hiểu context |
| 9 | AI có thể tốt hơn | Khi bị distract và quay lại task, mất thêm 10-15 phút để nhớ lại mình đang làm đến đâu | Developer ADHD | Xảy ra nhiều lần/ngày — context switching cost rất cao với ADHD |
| 10 | Tốn thời gian | Theo dõi stocks, email, Canvas deadline cùng lúc với coding — không có một nơi tổng hợp tất cả thành daily priority list | Bản thân | Phải check 4-5 nguồn khác nhau mỗi sáng để biết hôm nay ưu tiên gì |

---

## Top 3

| Rank | Problem | Vì sao chọn | Điều còn chưa chắc |
|---|---|---|---|
| 1 | Morning context overload — mở workspace xong vẫn không biết hôm nay ưu tiên gì | Workflow rõ, lặp lại hằng ngày, đã có baseline (script chạy nhưng chưa giải được phần tổng hợp), metric đo được | "Good enough" daily summary trông như thế nào |
| 2 | PR review bottleneck — tech lead phải đọc quá nhiều, developer phải ping nhiều lần | Pain thật từ nhiều người, impact rõ đến tiến độ team | Khó validate nhanh nếu không có data PR history |
| 3 | Vague requirements + client im lặng — developer không biết "done" nghĩa là gì, build xong bị yêu cầu làm lại | Hai evidence thật từ HMU và BlueOC, impact rõ (2 tuần work bị xóa, làm lại nhiều lần), ảnh hưởng cả team không chỉ cá nhân | Giải pháp AI ở bước nào trong vòng requirements chưa rõ |

---

## Problem Card #1 — Morning Context Overload

**Problem 1 câu:**
Mỗi sáng developer mất 15-20 phút mở workspace và đọc qua Gmail, work mail, Canvas, stocks để tự tổng hợp priority — dù đã có script auto-open, phần đọc và ra quyết định vẫn hoàn toàn thủ công.

**Actor:**
Developer/student có nhiều nguồn thông tin buổi sáng cần xử lý trước khi bắt đầu làm việc.

**Thời điểm / bối cảnh:**
Mỗi sáng khi bật máy, trước khi bắt đầu coding hoặc học.

**Current workflow:**
```
1. Bật máy — Python script tự mở các tab/app [2']
2. Đọc Gmail — tìm email quan trọng [3-5']
3. Đọc work mail — check task update [3-5']
4. Mở Canvas — check deadline [2-3']
5. Check stocks [2-3']
6. Tự tổng hợp trong đầu — hôm nay ưu tiên gì [3-5']
7. Bắt đầu làm việc
Tổng: 15-20 phút, bước 6 dễ bị skip hoặc làm sai
```

**Bottleneck:**
Bước 6 — không có gì tự động tổng hợp các nguồn thành một daily priority list. Phải tự đọc và tự ra quyết định từ nhiều nguồn rời rạc.

**Impact:**
15-20 phút/ngày × 7 ngày = 1.5-2.5 giờ/tuần chỉ để setup context buổi sáng. Với ADHD, nếu bước này rối hoặc có quá nhiều thứ cần đọc, dễ bị distract ngay từ đầu ngày.

**Success metric:**
Giảm thời gian từ lúc bật máy đến khi có daily priority list xuống dưới 3 phút. Không bỏ sót deadline hoặc task quan trọng.

**Non-AI alternative:**
Notion daily template + manual checklist mỗi sáng. Giảm được bước tìm kiếm nhưng vẫn phải tự đọc và tổng hợp.

**AI hypothesis:**
AI đọc qua email/Canvas/stocks summary, tổng hợp thành 3-5 priority items cho ngày hôm đó. Developer chỉ cần đọc output và bắt đầu làm.

**Quick gut:** Workflow.

### Draft current workflow
```
CURRENT STATE — 15-20 phút

[Script auto-open: 2']
→ [Đọc Gmail: 3-5']
→ [Đọc work mail: 3-5']         <-- 3 nguồn đọc riêng lẻ
→ [Check Canvas: 2-3']
→ [Check stocks: 2-3']
→ [Tự tổng hợp priority: 3-5'] <-- bottleneck, dễ bị distract
→ [Bắt đầu làm việc]
```

### Draft future workflow
```
FUTURE STATE — 3-5 phút

[Script auto-open: 2']
→ [AI đọc Gmail + Canvas + stocks: 1']      -- Workflow step
→ [AI output: top 3-5 priorities hôm nay]  -- Human reads
→ [Developer confirm và bắt đầu: 1-2']     -- Human boundary

Fallback: AI summary sai/thiếu → developer tự check nguồn gốc.
```

---

## Problem Card #2 — PR Review Bottleneck

**Problem 1 câu:**
Trong team project, mỗi PR mất 1-2 ngày để được review vì tech lead phải đọc hàng trăm dòng code và developer phải ping nhiều lần — làm chặn tiến độ cả team.

**Actor:**
Developer cần PR được approve và tech lead phải review nhiều PR cùng lúc.

**Thời điểm / bối cảnh:**
Sau mỗi feature hoàn thành, trước khi merge vào main branch.

**Current workflow:**
```
1. Developer push code lên branch
2. Tạo PR — viết description thủ công [10-15']
3. Ping tech lead trên chat để xin review
4. Tech lead đọc toàn bộ diff [20-40']
5. Tech lead comment hoặc approve
6. Developer fix nếu có comment [variable]
7. Ping lại để xin final approve
8. Merge
```

**Bottleneck:**
Bước 4 — tech lead phải đọc toàn bộ diff không có context rõ ràng. Bước 3+7 — communication overhead, dễ bị bỏ sót trong chat.

**Impact:**
1-2 ngày/PR × nhiều PR/sprint = tiến độ team bị chặn liên tục. Tech lead burned out với review. Developer frustrated vì chờ.

**Success metric:**
Giảm thời gian từ PR tạo đến approval xuống dưới 4 giờ. Giảm số lần ping cần thiết từ 3+ xuống còn 1.

**Non-AI alternative:**
PR template cố định + checklist trước khi tạo PR. Giảm thời gian đọc nhưng không tóm tắt được thay đổi tự động.

**AI hypothesis:**
AI đọc diff và tự generate PR description rõ ràng — what changed, why, impact, risk. Tech lead đọc summary trước khi đọc code, tiết kiệm thời gian hiểu context.

**Quick gut:** Workflow.

### Draft current workflow
```
CURRENT STATE — 1-2 ngày

[Push code]
→ [Viết PR description thủ công: 10-15'] <-- thường viết qua loa
→ [Ping tech lead]                        <-- dễ bị bỏ sót trong chat
→ [Tech lead đọc toàn bộ diff: 20-40']   <-- bottleneck
→ [Comment / approve]
→ [Fix + ping lại]                        <-- thêm 1 vòng chờ
→ [Merge]
```

### Draft future workflow
```
FUTURE STATE — dưới 4 giờ

[Push code]
→ [AI đọc diff → generate PR description: 1'] -- Workflow step
→ [Developer review + edit description: 5']   -- Human boundary
→ [Tech lead đọc AI summary trước code: 5']   -- Context rõ hơn
→ [Tech lead review code: 15-20']             -- Nhanh hơn vì có context
→ [Approve + merge]

Fallback: AI description sai/thiếu → developer tự viết lại thủ công.
```

---

## Problem Card #3 — Vague Requirements + Client Im Lặng

**Problem 1 câu:**
Trong dự án có client không technical, feedback mơ hồ ("UX bad", "tôi không thích") và client dần im lặng khiến developer không biết "done" nghĩa là gì — dẫn đến build sai, build lại, hoặc xóa cả feature sau nhiều tuần làm.

**Actor:**
Developer và tech lead trong team project có client bên ngoài hoặc stakeholder không technical.

**Thời điểm / bối cảnh:**
Suốt vòng đời dự án — đặc biệt rõ khi bắt đầu sprint mới hoặc khi nhận feedback sau demo.

**Current workflow:**
```
1. Team nhận yêu cầu từ client — thường bằng lời nói hoặc email chung chung
2. Developer tự diễn giải yêu cầu thành task
3. Build feature dựa trên diễn giải của mình [days-weeks]
4. Demo cho client
5. Client feedback mơ hồ: "không thích", "UI xấu", "không biết dùng"
6. Developer không biết sửa cụ thể chỗ nào
7. Hỏi lại client — client trả lời chậm hoặc không trả lời
8. Developer đoán và sửa, hoặc bỏ feature
```

**Bottleneck:**
Bước 2 và 5-7 — không có DoD rõ từ đầu, không có structured feedback template, không có cơ chế escalate khi client im lặng.

**Impact:**
HMU: chỉ gặp client 3-4 lần trong 7 tháng, 3 tháng cuối client hoàn toàn im lặng. Feature template bị build 2 tuần rồi xóa vì không có trong requirements thật. Team build dựa trên giả định suốt 3 tháng cuối.
BlueOC: CEO feedback "UX bad / tôi không biết dùng" không chỉ ra điểm cụ thể — developer phải đoán, làm lại nhiều lần, tốn thời gian mà vẫn không chắc đúng hướng.

**Success metric:**
Giảm số lần làm lại feature do hiểu sai requirements từ 2-3 lần/tháng xuống dưới 1 lần. Mỗi sprint bắt đầu với DoD có ít nhất 3 acceptance criteria đo được, không phải mô tả chung chung.

**Non-AI alternative:**
DoD checklist cứng + requirement sign-off trước khi bắt đầu sprint. Giảm được ambiguity nhưng không giúp khi client không responsive hoặc không biết diễn đạt yêu cầu.

**AI hypothesis:**
AI giúp convert feedback mơ hồ từ client thành structured acceptance criteria — "UX bad" → "button X không rõ label, flow Y cần ít hơn 3 bước, error message Z cần giải thích rõ hơn." Developer và client review list này trước khi bắt đầu build.

**Quick gut:** Workflow.

### Draft current workflow
```
CURRENT STATE — ambiguous, nhiều vòng lặp

[Nhận yêu cầu chung chung từ client]
→ [Developer tự diễn giải: days]
→ [Build feature: weeks]              <-- có thể build sai hướng
→ [Demo]
→ [Feedback mơ hồ: "không thích"]    <-- bottleneck 1
→ [Hỏi lại — client không trả lời]   <-- bottleneck 2
→ [Đoán và sửa hoặc xóa feature]     <-- wasted effort
```

### Draft future workflow
```
FUTURE STATE — rõ hơn trước khi build

[Nhận feedback/yêu cầu từ client]
→ [AI convert thành structured criteria: 5']   -- Workflow step
→ [Developer + client review list: 15-30']     -- Human boundary
→ [Sign off DoD trước khi build]
→ [Build với acceptance criteria rõ]
→ [Demo theo đúng criteria đã ký]

Fallback: Client không respond để review → escalate lên PM/supervisor,
không build cho đến khi có sign-off.
```

---

*01-individual-problem-scan — Day 02 Lab — Nguyen Hoang Minh*
