# Demo Guide — Day 7 RAG Lab (Kịch bản nói chi tiết)

**Nhóm:** Nguyen Hoang Minh, Duy, Nam, Dũng  
**Corpus:** 6 files trong `data/` — Internal Knowledge Assistant  
**Thời lượng gợi ý:** 10–12 phút (có thể rút còn 7 phút nếu bỏ failure case)

> File này là **script nói đầy đủ** — bạn có thể đọc gần như nguyên văn khi demo. Các đoạn trong `> blockquote` là lời nói. Phần **Hành động** là thao tác trên màn hình.

---

## Chuẩn bị kỹ thuật

```bash
pip install -r requirements.txt
```

`.env`:
```env
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
```

```bash
python app.py          # http://127.0.0.1:7860
pytest tests/ -v       # 42/42
```

**Trước khi lên trình bày:** mở sẵn Gradio, chọn strategy **Minh**, chạy thử 1 câu để store load xong (tránh đợi API lúc demo).

---

## Phân vai nhóm (ai nói phần nào)

| Thời điểm | Người nói | Nội dung |
|-----------|-----------|----------|
| 0:00–1:30 | **Minh** | Mở đầu + giải thích RAG pipeline + recursive chunking |
| 1:30–3:30 | **Duy** | Parent/child + metadata filter + demo Q2, Q3 |
| 3:30–5:30 | **Nam** | Document-structure + demo Q3, Q5 |
| 5:30–7:00 | **Dũng** | Semantic chunking + demo Q2 |
| 7:00–8:30 | **Minh** | So sánh Q3 Minh vs Duy + failure case |
| 8:30–9:30 | **Bất kỳ** | Kết luận + Q&A |

*Nếu chỉ 1 người demo, đọc hết theo thứ tự trên.*

---

# PHẦN 1 — KHÁI NIỆM NỀN (Minh nói)

## 1.1 Mở đầu

**Hành động:** Mở `http://127.0.0.1:7860`, chỉ vào title "Knowledge Base Agent".

> "Xin chào, nhóm em gồm Minh, Duy, Nam và Dũng. Hôm nay em demo **Lab 7 — Embedding & Vector Store**, xây dựng một chatbot tra cứu tài liệu nội bộ theo mô hình **RAG**.
>
> **RAG** viết tắt của *Retrieval-Augmented Generation*. Ý tưởng rất đơn giản: thay vì hỏi thẳng ChatGPT *'Python dùng để làm gì?'* và để nó tự trả lời từ kiến thức đã học, em **tìm đoạn tài liệu của công ty trước**, rồi mới đưa đoạn đó vào prompt để GPT trả lời **dựa trên tài liệu thật**.
>
> Lợi ích: câu trả lời **grounded** — có căn cứ, có thể truy vết nguồn. Hạn chế: nếu bước tìm tài liệu sai, GPT cũng trả lời sai hoặc từ chối — như em sẽ show ở cuối."

---

## 1.2 RAG là gì? Giải thích bằng ví dụ đời thường

> "Hãy tưởng tượng RAG giống thi **mở sách**:
>
> - **Không RAG:** Học sinh trả lời từ trí nhớ — có thể đúng, có thể bịa.
> - **Có RAG:** Học sinh được mở sách, tìm trang liên quan, rồi trả lời dựa trên trang đó.
>
> Trong code của em:
> - **Sách** = 6 file trong folder `data/`
> - **Tìm trang** = vector search (embedding + similarity)
> - **Đọc và trả lời** = GPT-4o-mini nhận context + câu hỏi"

---

## 1.3 Pipeline 5 bước — giải thích từng bước chi tiết

**Hành động:** Chỉ lần lượt vào dropdown Strategy, ô Active setup, ô Retrieved chunks, ô Agent answer.

### Bước 1: Load documents

> "Hệ thống đọc 6 file `.txt` và `.md`. Mỗi file được gán **metadata** — thông tin mô tả file, không nằm trong nội dung chính:
>
> | File | language | department | category |
> |------|----------|------------|----------|
> | python_intro.txt | en | support | reference |
> | vector_store_notes.md | en | engineering | technical |
> | rag_system_design.md | en | engineering | technical |
> | customer_support_playbook.txt | en | support | reference |
> | chunking_experiment_report.md | en | support | technical |
> | vi_retrieval_notes.md | **vi** | support | technical |
>
> Metadata giống **nhãn trên hồ sơ** — sau này em có thể nói *'chỉ tìm trong hồ sơ phòng kỹ thuật'* hoặc *'chỉ tìm tài liệu tiếng Việt'* trước khi search."

### Bước 2: Chunking — tại sao phải chia nhỏ?

> "**Chunking** là chia mỗi file dài thành nhiều **đoạn nhỏ** (chunk). Tại sao?
>
> Ví dụ `python_intro.txt` dài ~1,900 ký tự, nói về Python dùng cho automation, backend, data analysis. Nếu embed **cả file** thành 1 vector duy nhất, vector đó phải đại diện cho *tất cả* ý trong file — signal bị **loãng**.
>
> Khi user hỏi *'How does billing work?'*, vector của cả file Python có thể vẫn hơi giống câu hỏi (cùng corpus kỹ thuật) → retrieve nhầm. Chunk nhỏ hơn giúp mỗi vector đại diện **một ý cụ thể** → search chính xác hơn.
>
> **Đây là phần mỗi thành viên nhóm làm khác nhau** — cách chia chunk. Em sẽ giải thích 4 cách + 2 baseline."

### Bước 3: Embedding — text thành số như thế nào?

> "**Embedding** biến đoạn text thành một **vector số** — ví dụ 1,536 số thực (model `text-embedding-3-small` của OpenAI).
>
> Hai câu càng **giống nghĩa**, hai vector càng **gần nhau** trong không gian nhiều chiều. Em đo 'gần' bằng **cosine similarity** — score từ -1 đến 1, càng cao càng giống.
>
> Ví dụ:
> - *'Vector databases store embeddings'* vs *'A vector store keeps numerical representations'* → similarity **cao** (~0.7–0.8 với model thật)
> - *'The cat sat on the mat'* vs *'Stock prices rose today'* → similarity **thấp** hoặc âm
>
> Cosine similarity quan trọng hơn khoảng cách Euclidean vì embedding thường quan tâm **hướng** (nghĩa) hơn **độ dài** vector."

### Bước 4: Vector store — search hoạt động ra sao?

> "Sau khi embed, mỗi chunk được lưu vào **vector store** kèm:
> - `content` — nội dung text
> - `embedding` — vector số
> - `metadata` — source, language, department, ...
>
> Khi user hỏi câu hỏi:
> 1. Embed câu hỏi thành vector
> 2. So sánh với **tất cả** vector trong store (dot product / cosine)
> 3. Sort giảm dần theo score
> 4. Trả **top-k** chunk (em dùng k=3)
>
> Nếu có **metadata filter** — ví dụ `language=vi` — hệ thống **loại** chunk không khớp filter **trước**, rồi mới rank similarity. Điều này giúp không bị chunk tiếng Anh chen vào khi hỏi về tài liệu tiếng Việt."

### Bước 5: Agent — GPT trả lời thế nào?

> "Agent nhận top-3 chunk, ghép lại thành **context block**, rồi gửi prompt dạng:
>
> ```
> Context:
> [chunk 1]
> [chunk 2]
> [chunk 3]
>
> Question: What is Python used for?
> Answer:
> ```
>
> GPT-4o-mini có system message: *'Chỉ trả lời dựa trên context. Nếu context không đủ, nói không biết.'*
>
> Vì vậy nếu retrieve sai tài liệu, agent **từ chối** thay vì hallucinate — em sẽ demo failure case ở cuối."

---

# PHẦN 2 — 4 CHIẾN LƯỢC CHUNKING (chi tiết từng người)

---

## 2.1 Minh — Recursive Character Splitting

**Hành động:** Chọn dropdown **minh**. Chờ ô "Active setup" hiện `Chunks: 43`.

### Recursive chunking là gì?

> "**Recursive** nghĩa là **đệ quy** — thử tách theo ranh giới lớn trước, nếu vẫn quá dài thì tách nhỏ hơn, lặp lại cho đến khi mỗi mảnh ≤ `chunk_size`.
>
> Thứ tự separator em dùng (ưu tiên từ lớn → nhỏ):
>
> ```
> 1. "\n\n"   → đoạn văn (paragraph)
> 2. "\n"     → dòng mới
> 3. ". "     → kết thúc câu
> 4. " "      → khoảng trắng (từ)
> 5. ""       → cắt cứng từng ký tự (last resort)
> ```
>
> **Ví dụ cụ thể** với đoạn markdown:
>
> ```
> ## Retrieval Layer
>
> The retrieval layer embeds queries and searches the vector store.
> It also supports metadata filtering.
>
> ## Application Layer
> ...
> ```
>
> Bước 1: Tách `\n\n` → được 2 đoạn (Retrieval Layer + Application Layer).
> Bước 2: Mỗi đoạn < 400 ký tự → giữ nguyên, không cắt thêm.
> Bước 3: Nếu một đoạn dài 600 ký tự → tách tiếp bằng `\n`, rồi `. `, v.v.
>
> **Khác gì fixed-size?** Fixed-size cắt đúng ký tự thứ 400 — có thể cắt giữa từ *'embeddings'* thành *'embed'* và *'dings'*. Recursive cố giữ ranh giới tự nhiên trước."

### So với baseline

> "Em chọn `chunk_size=400`. Kết quả: **43 chunks** từ 6 file.
>
> So với baseline:
> - **Fixed-size** (35 chunks): cắt cứng, overlap 50 ký tự — đơn giản nhưng dễ mất ngữ cảnh ở ranh giới.
> - **Sentence** (32 chunks): gộp 3 câu/chunk — ít chunk nhất nhưng một chunk có thể dài 500+ ký tự, dense khó retrieve.
>
> Recursive của em ở giữa: nhiều chunk hơn sentence (chunk nhỏ hơn, focused hơn), ít hơn parent/child của Duy (99 chunks)."

### Demo Q1 — What is Python used for?

**Hành động:** Gõ câu hỏi → bấm Ask → chỉ vào Retrieved chunks và Agent answer.

> "Câu hỏi đầu tiên trong benchmark nhóm: *'What is Python used for?'*
>
> Kỳ vọng: retrieve từ `python_intro.txt`.
>
> Kết quả của em:
> - Top-1: `python_intro.txt` — score **0.701**
> - Top-2: `python_intro.txt` — score **0.623**
> - Top-3: `python_intro.txt` — score **0.559**
>
> Cả 3 slot đều đúng tài liệu — **3/3 relevant**. Score giảm dần vì chunk 2 và 3 là đoạn khác trong cùng file, ít match trực tiếp câu hỏi hơn nhưng vẫn về Python.
>
> Agent answer sẽ nói: automation, backend/API, data analysis, scientific computing, ML — khớp gold answer trong báo cáo. Em có thể chỉ vào chunk preview và nói: *'Mỗi câu trong answer đều có thể trace về đoạn này.'*"

### Demo Q3 — điểm yếu cần nói thẳng

**Hành động:** Hỏi `What is the RAG system architecture?`

> "Đây là câu hỏi **khó hơn** vì từ *'system architecture'* xuất hiện ở nhiều file.
>
> Kết quả Minh:
> - Top-1: `rag_system_design.md` — **0.544** ✓ (đúng)
> - Top-2: `rag_system_design.md` — **0.360** ✓
> - Top-3: `python_intro.txt` — **0.324** ✗ (nhiễu)
>
> Top-1 đúng nên rubric vẫn **2/2 điểm**. Nhưng slot 3 là `python_intro.txt` — vì file đó nói *'Python is widely used for... backend services, data analysis'* — từ *'services'* và *'systems'* gần nghĩa *'architecture'* trong embedding space.
>
> **Bài học:** Recursive chunking alone không loại được false positive từ doc khác department. Cần metadata filter — Duy và Nam sẽ show ngay sau."

---

## 2.2 Duy — Parent/Child Chunking

**Hành động:** Đổi dropdown sang **duy**. Chờ `Chunks: 99`.

### Parent/child là gì?

> "Parent/child chunking giải quyết **mâu thuẫn cổ điển** trong RAG:
>
> - Chunk **nhỏ** → search chính xác hơn (match câu hỏi cụ thể)
> - Chunk **lớn** → agent có đủ ngữ cảnh để trả lời (không bị mất ý)
>
> Duy chia **hai tầng**:
>
> | Tầng | Kích thước | Mục đích |
> |------|------------|----------|
> | **Parent** | ~700 ký tự | Giữ ngữ cảnh section lớn |
> | **Child** | ~220 ký tự | Dùng để **search** (embed & index) |
>
> **Quy trình:**
> 1. Chia file thành parent bằng RecursiveChunker(700)
> 2. Chia mỗi parent thành child bằng RecursiveChunker(220)
> 3. Chỉ **child** được embed và đưa vào vector store
> 4. Metadata child lưu `parent_preview` — 300 ký tự đầu của parent
>
> **Ví dụ:** Parent là cả section *'## Retrieval Layer — embed query, search store, apply filter'*. Child 1: *'embed query and search the vector store'*. Child 2: *'apply metadata filter before ranking'*.
>
> Khi search match child 2, agent vẫn biết nó thuộc section Retrieval Layer nhờ `parent_preview`."

### Tại sao 99 chunks?

> "6 file × nhiều parent × mỗi parent 2–4 child → **99 chunks** — nhiều nhất nhóm. Trade-off:
> - ✓ Search granular hơn — câu hỏi cụ thể match child nhỏ
> - ✗ Embed 99 lần, search 99 vectors — chậm và tốn API hơn Minh (43 chunks)"

### Metadata filter — Duy giải thích

> "Ngoài chunking, Duy dùng `search_with_filter()` — **lọc metadata trước khi tính similarity**.
>
> Logic trong code (`src/store.py`):
> 1. Nhận filter, ví dụ `{'department': 'engineering'}`
> 2. Giữ chỉ chunk có `metadata['department'] == 'engineering'`
> 3. Trên tập đã lọc, embed query và rank
>
> **Tại sao Q2/Q3 dùng filter?**
> - Q2 *'How does a vector store work?'* → tài liệu đúng là `vector_store_notes.md` (engineering)
> - Không filter: chunk từ `chunking_experiment_report.md` (support) vẫn có thể lọt top-3 vì cũng nói về chunking/embed
> - Filter `department=engineering`: loại hết support docs → top-3 sạch hơn"

### Demo Q2 — vector store

**Hành động:** Hỏi `How does a vector store work?`

> "So sánh Minh vs Duy trên cùng câu:
>
> | | Minh (no filter) | Duy (department=engineering) |
> |--|------------------|------------------------------|
> | Top-1 score | 0.692 | **0.738** |
> | Top-3 | 3/3 vector_store_notes | 3/3 vector_store_notes |
>
> Duy score cao hơn vì pool candidate nhỏ hơn — không bị dilute bởi doc khác department. Top-3 scores của Duy rất sát nhau (0.738, 0.706, 0.647) — cho thấy nhiều child chunk trong cùng file đều relevant, parent/child đã chia đúng chủ đề."

### Demo Q3 — RAG architecture (highlight chính)

**Hành động:** Hỏi `What is the RAG system architecture?`

> "Đây là demo **quan trọng nhất** để thấy filter + chunking:
>
> | | Minh | Duy |
> |--|------|-----|
> | Top-1 | rag_system_design.md (0.544) | rag_system_design.md (**0.609**) |
> | Top-3 purity | **2/3** — có python_intro | **3/3** — toàn rag_system_design |
>
> `python_intro.txt` có `department=support`. Filter `engineering` loại nó hoàn toàn. Cả 3 chunk đều từ đúng tài liệu thiết kế RAG — agent nhận context sạch, answer chi tiết hơn về ingestion / retrieval / application layer."

### Demo Q4 — support issues

**Hành động:** Hỏi `What are common customer support issues?`

> "Q4 Duy dùng filter ngược: `department=support`.
>
> Top-1: `customer_support_playbook.txt` — score **0.493** (cao hơn Minh 0.473).
>
> Câu hỏi về support → filter support → chỉ search trong playbook và tài liệu support khác. Gold answer: account setup, billing errors, password recovery, service limitations — agent trả lời đúng các ý này."

---

## 2.3 Nam — Document-Structure Chunking

**Hành động:** Đổi sang **nam**. Chờ `Chunks: 36`.

### Document-structure là gì?

> "Nam tận dụng **cấu trúc có sẵn** trong tài liệu — đặc biệt markdown headings.
>
> **Quy tắc:**
> 1. Split tại mỗi dòng bắt đầu bằng `#`, `##`, hoặc `###`
> 2. Mỗi phần = một **section** (heading + nội dung bên dưới)
> 3. Section ≤ 500 ký tự → **1 chunk** (giữ nguyên cả section)
> 4. Section > 500 ký tự → fallback RecursiveChunker(500) chia nhỏ
> 5. Metadata: `section_title` — ví dụ `## Retrieval Layer`
>
> **Ví dụ với `rag_system_design.md`:**
>
> ```
> # RAG System Design          → chunk 1 (section_title: "# RAG System Design")
> ## Ingestion Pipeline        → chunk 2
> ## Retrieval Layer           → chunk 3
> ## Application Layer         → chunk 4
> ```
>
> Mỗi chunk = **một mục logic** trong tài liệu — giống cách người đọc skim qua mục lục.
>
> **Hạn chế:** File `.txt` không có `# heading` — như `python_intro.txt` — toàn file được coi là 1 section. Lợi thế rõ nhất ở file `.md` có cấu trúc."

### Tại sao chỉ 36 chunks?

> "Ít nhất nhóm vì mỗi section ngắn = 1 chunk, không chia thừa. `rag_system_design.md` có ~4–5 section → ~5 chunk thay vì 21 chunk như recursive nhỏ.
>
> Ít chunk = index nhỏ, search nhanh. Nhưng nếu section quá dài và phải split, có thể mất tính 'một section một ý'."

### Filter `category=technical`

> "Nam dùng `category=technical` cho Q2/Q3 thay vì `department`.
>
> - `vector_store_notes.md` → category=technical ✓
> - `rag_system_design.md` → category=technical ✓
> - `python_intro.txt` → category=**reference** ✗ (bị loại ở Q3)
> - `customer_support_playbook.txt` → category=reference (không ảnh hưởng Q4 vì Nam không filter Q4)
>
> Filter theo **loại tài liệu** (technical vs reference) thay vì **phòng ban** — góc nhìn khác Duy nhưng cùng mục tiêu: thu hẹp candidate pool."

### Demo Q3 — score cao nhất

**Hành động:** Hỏi `What is the RAG system architecture?`

> "Nam đạt **top-1 score cao nhất ở Q3: 0.619** — cao hơn Duy (0.609) và Minh (0.544).
>
> Top-3: **3/3** `rag_system_design.md` (0.619, 0.397, 0.284).
>
> Lý do: chunk theo section nên chunk top-1 có thể là nguyên section *'## Proposed Architecture — Ingestion, Retrieval, Application'* — embedding match tốt với câu hỏi *'RAG system architecture'* vì cùng từ khóa và cùng cấu trúc ý."

### Demo Q5 — Vietnamese (highlight)

**Hành động:** Hỏi `What are common retrieval failure cases in Vietnamese?`

> "Q5 là câu **đặc biệt** — câu hỏi tiếng Anh nhưng đáp án nằm trong `vi_retrieval_notes.md` tiếng Việt.
>
> Tất cả strategy đều filter `language=vi` trước — bắt buộc, nếu không sẽ retrieve doc tiếng Anh.
>
> | Strategy | Top-1 score |
> |----------|-------------|
> | **Nam** | **0.614** ← cao nhất |
> | Minh | 0.587 |
> | Duy | 0.496 |
> | Dũng | 0.490 |
>
> Nam thắng vì: file `vi_retrieval_notes.md` có section tiếng Việt liền mạch — *'tài liệu cũ xếp hạng cao'*, *'keyword mismatch'*, *'song ngữ'* — không bị cắt giữa câu. Chunk section giữ nguyên đoạn văn tiếng Việt → vector đại diện tốt cho failure cases.
>
> Agent answer grounded: liệt kê đúng 3 failure case trong tài liệu. Em chỉ vào chunk preview tiếng Việt và đối chiếu từng ý trong answer."

---

## 2.4 Dũng — Semantic Chunking

**Hành động:** Đổi sang **dung**. Chờ load (~30s–2 phút lần đầu vì embed từng câu). `Chunks: 81`.

### Semantic chunking là gì?

> "Ba strategy trước chia theo **cấu trúc ký tự** (kích thước, heading, parent/child). Semantic chia theo **nghĩa** — nội dung nào liên quan thì gộp chung chunk.
>
> **Thuật toán (trong `src/team_strategies.py`):**
>
> ```
> 1. Tách text thành danh sách câu (split sau . ! ?)
> 2. Embed từng câu bằng OpenAI  →  vector_1, vector_2, ...
> 3. Bắt đầu group = [câu_1]
> 4. Với mỗi câu tiếp theo:
>    - Tính cosine_similarity(câu_trước, câu_này)
>    - Nếu similarity ≥ 0.55 VÀ gộp không vượt 500 ký tự:
>        → thêm vào group hiện tại
>    - Ngược lại:
>        → đóng group, mở group mới
> 5. Mỗi group = 1 chunk
> ```
>
> **Ví dụ minh họa:**
>
> ```
> Câu 1: "A vector store keeps embeddings."           → embed → v1
> Câu 2: "Queries are embedded and ranked by similarity." → embed → v2
>   similarity(v1, v2) = 0.72 ≥ 0.55 → GỘP
> Câu 3: "The support team handles billing errors."     → embed → v3
>   similarity(v2, v3) = 0.31 < 0.55 → CHUNK MỚI
> ```
>
> Kết quả: Chunk 1 = câu 1+2 (cùng chủ đề vector store). Chunk 2 = câu 3 (support billing)."

### Threshold 0.55 — giải thích nếu bị hỏi

> "0.55 là ngưỡng em chọn sau thử nghiệm. Thấp hơn (0.4) → gộp quá nhiều câu không liên quan. Cao hơn (0.7) → quá nhiều chunk 1 câu, gần giống sentence chunking. 0.55 cân bằng cho corpus nhóm."

### Chi phí — nói thẳng

> "Nhược điểm lớn nhất: phải gọi OpenAI API **cho mỗi câu** lúc index — không phải lúc search. Corpus 6 file ~ hundreds of sentences → index mất **~2 phút** và tốn token.
>
> Ba strategy kia chỉ embed **sau khi** đã chia chunk xong — 1 API call/chunk. Semantic = 1 API call/câu **+** 1 API call/chunk khi index.
>
> 81 chunks — giữa Minh (43) và Duy (99). Phù hợp khi tài liệu **không có heading**, **không có cấu trúc** — ví dụ email chain, chat log, PDF convert text lộn xộn."

### Demo Q2

**Hành động:** Hỏi `How does a vector store work?`

> "Top-1: `vector_store_notes.md` — score **0.726** (ngang Nam).
>
> Các câu trong file mô tả workflow *'chunk → embed → store → query → rank'* được semantic gộp thành chunk coherent — vector đại diện cả pipeline, match tốt câu hỏi *'how does it work'*."

### Demo Q3 — điểm yếu

> "Q3 giống Minh: top-3 chỉ **2/3**, slot 3 là `python_intro.txt` (0.324).
>
> Semantic giỏi gộp câu **trong** một chủ đề nhưng không **loại** chủ đề khác. `python_intro` nói backend services — embedding space gần *'system architecture'*. Cần thêm metadata filter như Duy/Nam nếu muốn top-3 sạch."

---

# PHẦN 3 — WALKTHROUGH 5 BENCHMARK QUERIES (bảng đầy đủ)

Dùng khi giảng viên hỏi *"cho tôi xem từng câu"* hoặc khi cần số liệu chính xác.

## Q1: What is Python used for?

| Strategy | Top-1 | Score | Top-3 purity | Filter |
|----------|-------|-------|--------------|--------|
| Minh | python_intro.txt | 0.701 | 3/3 | none |
| Duy | python_intro.txt | 0.696 | 3/3 | none |
| Nam | python_intro.txt | 0.701 | 3/3 | none |
| Dũng | python_intro.txt | 0.697 | 3/3 | none |

**Nói gì:** "Q1 dễ — câu hỏi cụ thể, chỉ một file relevant. Cả 4 strategy đều 3/3. Sentence baseline thậm chí cao nhất (0.708) vì gộp câu giữ nguyên đoạn 'Python is used for automation, backend...'."

**Gold answer cần nhắc:** automation, backend/API, data analysis, ML (FastAPI, Django, pandas, PyTorch).

---

## Q2: How does a vector store work?

| Strategy | Top-1 | Score | Top-3 purity | Filter |
|----------|-------|-------|--------------|--------|
| Minh | vector_store_notes.md | 0.692 | 3/3 | none |
| **Duy** | vector_store_notes.md | **0.738** | 3/3 | department=engineering |
| Nam | vector_store_notes.md | 0.726 | 3/3 | category=technical |
| Dũng | vector_store_notes.md | 0.726 | 3/3 | none |

**Nói gì:** "Duy thắng score nhờ filter. Gold answer: chunk → embed → store vector + metadata → embed query → rank by similarity — chỉ vào chunk và đọc 4 bước."

---

## Q3: What is the RAG system architecture? ⭐ câu hay bị hỏi nhất

| Strategy | Top-1 | Score | Top-3 purity | Filter |
|----------|-------|-------|--------------|--------|
| Minh | rag_system_design.md | 0.544 | **2/3** | none |
| Duy | rag_system_design.md | 0.609 | **3/3** | department=engineering |
| **Nam** | rag_system_design.md | **0.619** | **3/3** | category=technical |
| Dũng | rag_system_design.md | 0.538 | **2/3** | none |

**Nói gì:** "Q3 phân biệt rõ strategy. Minh và Dũng không filter → python_intro lọt top-3. Duy và Nam filter → 3/3 sạch. Nam score cao nhất nhờ section chunk + category filter. Gold answer: 3 layer — ingestion, retrieval, application."

**Demo side-by-side (nhấn mạnh):**
1. Minh → show python_intro ở slot 3
2. Duy → cùng câu → slot 3 là rag_system_design
3. "Cùng corpus, cùng embedding, khác chunking + filter → khác retrieval quality"

---

## Q4: What are common customer support issues?

| Strategy | Top-1 | Score | Top-3 purity | Filter |
|----------|-------|-------|--------------|--------|
| Minh | customer_support_playbook.txt | 0.473 | 3/3 | none |
| **Duy** | customer_support_playbook.txt | **0.493** | 3/3 | department=support |
| Nam | customer_support_playbook.txt | 0.473 | 3/3 | none |
| Dũng | customer_support_playbook.txt | 0.451 | 3/3 | none |

**Nói gì:** "Q4 scores thấp hơn Q1–Q3 (0.45–0.49) vì nhiều doc đều nhắc 'support' hoặc 'customer'. Vẫn đúng top-1. Gold: account setup, billing, password, service limits."

---

## Q5: What are common retrieval failure cases in Vietnamese?

| Strategy | Top-1 | Score | Top-3 purity | Filter |
|----------|-------|-------|--------------|--------|
| Minh | vi_retrieval_notes.md | 0.587 | 3/3 | language=vi |
| Duy | vi_retrieval_notes.md | 0.496 | 3/3 | language=vi |
| **Nam** | vi_retrieval_notes.md | **0.614** | 3/3 | language=vi |
| Dũng | vi_retrieval_notes.md | 0.490 | 3/3 | language=vi |

**Nói gì:** "Q5 test multilingual + filter. Không có filter `language=vi` thì `vector_store_notes.md` tiếng Anh có thể lọt. Nam thắng score — section chunk giữ tiếng Việt liền mạch. Gold: tài liệu cũ rank cao, keyword mismatch, song ngữ."

---

# PHẦN 4 — FAILURE CASE (Minh demo, ~2 phút)

**Hành động:**
1. Đổi LLM Provider → `mock` (hoặc xóa API key tạm)
2. Strategy: Minh
3. Hỏi: `What is Python used for?`

> "Em muốn show **failure thật** em gặp lúc đầu lab — trước khi sửa pipeline.
>
> **Cấu hình lỗi:**
> - Embedder: **MockEmbedder** — hash text thành vector deterministic, **không hiểu ngữ nghĩa**
> - Index: **nguyên file** — 6 documents, không chunk
>
> **Triệu chứng:**
> - Top-1: `chunking_experiment_report.md` — score chỉ **0.117**
> - Không phải `python_intro.txt`
>
> **Agent GPT-4o-mini trả lời:**
> *'The provided context does not contain information about the uses of Python.'*
>
> **Phân tích — đừng đổ lỗi LLM:**
> - LLM **đúng** khi từ chối — context retrieve về chunking experiment, không có gì về Python use cases
> - Lỗi ở **retrieval layer**: (1) mock embed không phân biệt 'Python' vs 'chunking', (2) whole-file index signal loãng
>
> **Sau khi sửa:**
> - `RecursiveChunker(400)` → 43 chunks
> - `text-embedding-3-small` → top-3 toàn python_intro, score 0.55–0.70
> - Agent trả lời grounded
>
> **Bài học cho production:** Luôn log `top-k + score + source` trước khi blame LLM. Nếu top-1 score < 0.3, nên trả *'không đủ dữ liệu'* thay vì đưa context nhiễu vào GPT."

**Hành động:** Đổi lại `openai` provider → chạy lại cùng câu → show fix.

---

# PHẦN 5 — ĐỌC MÀN HÌNH GRADIO (giải thích từng ô)

Khi kết quả hiện ra, chỉ vào từng phần:

| Ô UI | Nói gì |
|------|--------|
| **Chunking strategy** | "Đây là phần Phase 2 nhóm — mỗi người một method. Đổi strategy → rebuild index với chunk khác nhau." |
| **Active setup** | "Dòng này cho biết: strategy đang chạy, LLM backend, embedding model, **số chunk indexed**. Ví dụ `Chunks: 43` = 43 vectors trong store." |
| **Retrieved chunks** | "Top-k kết quả search. Mỗi dòng: **score** (cosine similarity), **source** (file gốc), **preview** (200 ký tự đầu chunk). Score cao = embedding gần câu hỏi hơn." |
| **Agent answer** | "GPT synthesize từ 3 chunk trên. Em kiểm tra grounding bằng cách đối chiếu từng câu answer với preview chunk." |
| **Top-k slider** | "k=3 mặc định. Tăng k=5 có thể thêm context nhưng cũng thêm nhiễu. Giảm k=1 tiết kiệm token nhưng có thể thiếu ý." |

---

# PHẦN 6 — KẾT LUẬN

> "Tóm lại nhóm em đã:
>
> 1. **Implement đầy đủ** RAG pipeline: chunking, EmbeddingStore (search, filter, delete), KnowledgeBaseAgent
> 2. **4 team strategies** + 2 baselines, so sánh trên 5 benchmark với OpenAI embedding thật
> 3. **Tất cả đạt 10/10** retrieval rubric — nhưng chất lượng top-3 và score khác nhau
>
> **Khuyến nghị nếu deploy thật:**
> - Corpus có markdown structure → **Nam** (doc-structure) + filter
> - Cần search chi tiết + context dài → **Duy** (parent/child) + filter
> - Pipeline đơn giản, maintain dễ → **Minh** (recursive)
> - Tài liệu unstructured, không heading → **Dũng** (semantic), chấp nhận chi phí index
>
> **Điều quan trọng nhất em học:** RAG fail ở retrieval, không phải generation. Chunking + embedding thật + metadata filter quyết định chất lượng hơn việc đổi sang GPT-4.
>
> Cảm ơn thầy/cô. Nhóm sẵn sàng trả lời câu hỏi."

---

# PHẦN 7 — CÂU HỎI THƯỜNG GẶP (Q&A)

### "Tại sao không dùng ChromaDB / Pinecone thật?"

> "Lab hỗ trợ ChromaDB fallback trong `EmbeddingStore`, nhưng em dùng in-memory list cho demo đơn giản. Logic search/filter giống nhau — chỉ khác backend lưu trữ. Production sẽ cần DB scale được."

### "top_k=3 có đủ không?"

> "Với corpus 6 file nhỏ, k=3 đủ. Production corpus lớn có thể cần k=5–10 hoặc dùng reranker. Em chọn k=3 vì gold answer thường nằm trong 1–2 chunk."

### "Score 0.54 có thấp không?"

> "Cosine similarity 0.5–0.7 là bình thường cho query-doc match. Quan trọng là **relative ranking** — top-1 phải đúng doc và score gap với top-2 nhiễu. Q3 score 0.54 thấp hơn Q1 (0.70) vì câu hỏi ambiguous hơn."

### "Filter có làm mất kết quả tốt không?"

> "Có thể — nếu metadata gán sai. Ví dụ nếu `python_intro` gán nhầm `department=engineering`, filter sẽ include nó ở Q3. Metadata schema phải chính xác. Em gán trong `bootstrap.py` theo tên file."

### "Semantic vs recursive — chọn cái nào?"

> "Recursive: nhanh, rẻ, đủ tốt cho markdown/txt có đoạn văn. Semantic: tốt hơn cho text lộn xộn, nhưng index chậm + tốn API. Không có silver bullet."

### "Agent có hallucinate không?"

> "Với setup hiện tại, ít — vì system prompt yêu cầu grounded. Khi retrieve sai (failure case), agent từ chối. Rủi ro hallucinate tăng khi top-1 đúng doc nhưng chunk không chứa đáp án — GPT có thể suy diễn từ context gần đúng."

### "42 tests pass nghĩa là gì?"

> "Phase 1 cá nhân: SentenceChunker, RecursiveChunker, compute_similarity, EmbeddingStore (add/search/filter/delete), KnowledgeBaseAgent. 42/42 = core implementation đúng spec lab, tách biệt với team strategy comparison."

---

# PHỤ LỤC — Số liệu & files

## Bảng tổng hợp

| Strategy | Chunks | Rubric | Index cost | Best query |
|----------|--------|--------|------------|------------|
| Minh — Recursive | 43 | 10/10 | Thấp | Q5 (0.587) |
| Duy — Parent/child | 99 | 10/10 | Cao | Q2 (0.738) |
| Nam — Doc-structure | 36 | 10/10 | Thấp nhất | Q5 (0.614), Q3 (0.619) |
| Dũng — Semantic | 81 | 10/10 | Cao nhất (embed/câu) | Q2 (0.726) |
| Baseline fixed | 35 | 10/10 | Thấp | — |
| Baseline sentence | 32 | 10/10 | Thấp | Q1 (0.708) |

## Lệnh tái tạo số liệu

```bash
python scripts/compare_strategies.py   # → report/compare_results.json
python scripts/run_benchmarks.py       # Minh strategy + agent answers
pytest tests/ -v
```

## Files

| File | Vai trò |
|------|---------|
| `src/chunking.py` | Recursive, Sentence, FixedSize (Minh + baselines) |
| `src/team_strategies.py` | ParentChild, DocumentStructure, Semantic (Duy, Nam, Dũng) |
| `src/bootstrap.py` | `build_rag_system(strategy_key=...)` |
| `src/store.py` | `search`, `search_with_filter` |
| `src/agent.py` | RAG prompt + LLM call |
| `app.py` | Gradio demo |
| `report/REPORT.md` | Báo cáo đầy đủ |
| `report/compare_results.json` | Raw benchmark numbers |
