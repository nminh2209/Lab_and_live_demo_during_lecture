# Lab 18 — Production RAG Pipeline: Detailed Analysis Report

**Author:** Nguyễn Hoàng Minh  
**Course:** AICB-P2T3 · Day 18 — Production RAG  
**Date:** 22 June 2026  
**Repository:** Day18-Track3-Production-RAG-batch-2

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Scope & Architecture](#2-project-scope--architecture)
3. [Corpus & Evaluation Setup](#3-corpus--evaluation-setup)
4. [Module Implementation Summary](#4-module-implementation-summary)
5. [Pipeline Run — Latency & Cost](#5-pipeline-run--latency--cost)
6. [RAGAS Evaluation — Full Analysis](#6-ragas-evaluation--full-analysis)
7. [Failure Taxonomy & Root Causes](#7-failure-taxonomy--root-causes)
8. [Naive vs Production — Why Baseline Won](#8-naive-vs-production--why-baseline-won)
9. [Rubric Self-Assessment](#9-rubric-self-assessment)
10. [Recommendations & Next Steps](#10-recommendations--next-steps)
11. [Conclusion](#11-conclusion)

---

## 1. Executive Summary

This lab implements a **full production RAG pipeline** for Vietnamese HR/IT policy documents:

```
M1 Chunking → M5 Enrichment → M2 Hybrid Search → M3 Reranking → LLM Answer → M4 RAGAS Eval
```

| Item | Result |
|------|--------|
| Unit tests | **37/37 passed** |
| Pipeline | **Exit code 0** (end-to-end) |
| Test questions | 20 Q&A pairs |
| Documents indexed | 26 markdown + 1 PDF (2 scan PDFs skipped) |
| Production chunks | 100 (hierarchical children) |
| Baseline chunks | 57 (basic paragraphs) |
| Total pipeline runtime | **~22 minutes** (1,342 s) |

**Headline result:** Production pipeline is architecturally superior but **underperforms naive baseline** on faithfulness (-9.2%) and context recall (-13.3%). The primary lesson: **complexity must be validated metric-by-metric** — more components do not guarantee better answers.

---

## 2. Project Scope & Architecture

### 2.1 Pipeline Diagram

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐
│ 26 docs     │───▶│ M1 Chunking  │───▶│ 100 child chunks        │
│ (data/*.md) │    │ hierarchical │    │ parent_id linked        │
└─────────────┘    └──────────────┘    └───────────┬─────────────┘
                                                   │
                       ┌───────────────────────────▼──────────────┐
                       │ M5 Enrichment (combined, 1 API/chunk)    │
                       │ summary + HyQA + context + metadata        │
                       └───────────────────────────┬──────────────┘
                                                   │
         ┌─────────────────────────────────────────▼────────────────────────┐
         │ M2 Hybrid Search                                                    │
         │  ├─ BM25 (underthesea segmentation)                                │
         │  ├─ Dense (BAAI/bge-m3 → Qdrant)                                   │
         │  └─ RRF fusion (k=60) → top-20                                     │
         └─────────────────────────────────────────┬────────────────────────┘
                                                   │
                       ┌───────────────────────────▼──────────────┐
                       │ M3 CrossEncoder Reranker                   │
                       │ BAAI/bge-reranker-v2-m3 → top-3            │
                       └───────────────────────────┬──────────────┘
                                                   │
                       ┌───────────────────────────▼──────────────┐
                       │ GPT-4o-mini answer generation            │
                       └───────────────────────────┬──────────────┘
                                                   │
                       ┌───────────────────────────▼──────────────┐
                       │ M4 RAGAS (4 metrics × 20 questions)      │
                       └──────────────────────────────────────────┘
```

### 2.2 Naive Baseline (comparison)

| Component | Naive | Production |
|-----------|-------|------------|
| Chunking | `chunk_basic()` paragraphs ~500 chars | `chunk_hierarchical()` child 256 chars |
| Enrichment | None | M5 combined LLM call |
| Search | Dense only (`bge-m3`) | BM25 + Dense + RRF |
| Reranking | None | Cross-encoder top-3 |
| Collection | `lab18_naive` | `lab18_production` |

---

## 3. Corpus & Evaluation Setup

### 3.1 Document Corpus

| Category | Examples | Notes |
|----------|----------|-------|
| Leave policies | `nghi_phep_nam_v2023.md`, `nghi_phep_nam_v2024.md` | Version conflict test |
| IT security | `mat_khau_v1.md`, `mat_khau_v2.md`, `vpn_truy_cap.md` | v1 vs v2 policy |
| HR / salary | `bang_luong_2024.md`, `thu_viec.md` | Numeric + classification |
| Procurement | `mua_sam.md`, `chi_phi_expense.md` | Approval thresholds |
| Compliance | `phan_loai_du_lieu.md`, `bao_mat_su_co.md` | Multi-hop |

- **Loaded:** 26 documents  
- **Skipped:** 2 scanned PDFs (no text layer, OCR required)

### 3.2 Test Set (20 questions)

Implicit question types in `test_set.json`:

| Type | Count (approx.) | Example |
|------|-----------------|---------|
| Simple lookup | ~8 | "Phụ cấp ăn trưa bao nhiêu?" |
| Version / superseded policy | ~4 | Password v2.0 vs v1.0, nghỉ phép v2024 |
| Negation | ~4 | "Thử việc có được nghỉ phép không?" |
| Multi-hop | ~3 | Senior 9 năm: phép + lương |
| Numeric reasoning | ~3 | Tạm ứng quá hạn pro-rata |
| Ambiguous / compound | ~2 | Laptop 30M: ai duyệt + CNTT cần gì |

---

## 4. Module Implementation Summary

### M1 — Advanced Chunking (`src/m1_chunking.py`)

| Strategy | Function | Key parameters | Role in pipeline |
|----------|----------|----------------|------------------|
| Semantic | `chunk_semantic()` | threshold=0.85, MiniLM-L6-v2 | Groups sentences by cosine sim |
| Hierarchical | `chunk_hierarchical()` | parent=2048, child=256 | **Used in production** |
| Structure-aware | `chunk_structure_aware()` | regex `#{1,3}` headers | Preserves section metadata |

**Tests:** 13/13 pass

### M2 — Hybrid Search (`src/m2_search.py`)

| Component | Implementation detail |
|-----------|----------------------|
| `segment_vietnamese()` | `underthesea.word_tokenize` + `replace("_", " ")` |
| `BM25Search` | `rank_bm25.BM25Okapi` on segmented tokens |
| `DenseSearch` | `bge-m3` (1024-dim) → Qdrant `query_points()` |
| `reciprocal_rank_fusion()` | score(d) = Σ 1/(k + rank + 1), k=60 |

**Tests:** 5/5 pass

### M3 — Reranking (`src/m3_rerank.py`)

- Model: `BAAI/bge-reranker-v2-m3` via `sentence_transformers.CrossEncoder`
- Input: top-20 hybrid results → Output: top-3 `RerankResult`
- Verified: "nghỉ phép" ranks above "VPN" in unit test

**Tests:** 5/5 pass

### M4 — RAGAS Evaluation (`src/m4_eval.py`)

| Metric | What it measures |
|--------|------------------|
| Faithfulness | Answer grounded in retrieved context |
| Answer relevancy | Answer addresses the question |
| Context precision | Retrieved chunks are relevant |
| Context recall | Ground-truth info present in context |

- `failure_analysis()`: sorts by avg metric → bottom-N with diagnostic tree

**Tests:** 4/4 pass

### M5 — Enrichment (`src/m5_enrichment.py`)

- **Mode used:** `_enrich_single_call()` — 1 GPT-4o-mini call per chunk (bonus +2)
- Output: summary, HyQA questions, contextual prepend, auto metadata
- Fallback: extractive heuristics when no API key

**Tests:** 10/10 pass

---

## 5. Pipeline Run — Latency & Cost

Measured from `main.py` run (22 Jun 2026):

| Step | Duration | Notes |
|------|----------|-------|
| M1 Chunking | 0.1 s | 100 child chunks from 26 docs |
| M5 Enrichment | **396.6 s** | 100 × GPT-4o-mini calls (~4 s/call) |
| M2 Indexing | 64.7 s | BM25 in-memory + bge-m3 encode + Qdrant upsert |
| M3 Reranker load | ~0 s | Cached from prior pytest |
| 20 query + LLM answers | ~included in eval | GPT-4o-mini per question |
| RAGAS evaluation | 36.8 s | 80 judge calls (4 metrics × 20 Q) |
| **Total** | **1,342 s (~22 min)** | Dominated by enrichment |

### Cost drivers (estimated)

| API usage | Calls | Model |
|-----------|-------|-------|
| Enrichment | 100 | gpt-4o-mini |
| Answer generation | 20 | gpt-4o-mini |
| RAGAS judges | ~80 | via ragas (OpenAI backend) |
| **Rough total** | **~200 LLM calls** | Per full pipeline run |

**Optimization opportunity:** Batch enrichment, cache enriched chunks to disk, skip re-enrichment on re-index.

---

## 6. RAGAS Evaluation — Full Analysis

### 6.1 Aggregate Scores

| Metric | Naive | Production | Δ | Interpretation |
|--------|-------|------------|---|----------------|
| **Faithfulness** | 0.8167 | 0.7250 | **-0.0917** | Production answers less grounded / more "Không tìm thấy" |
| **Answer Relevancy** | 0.7203 | 0.7209 | +0.0007 | Flat — question understanding similar |
| **Context Precision** | 0.9250 | 0.8875 | -0.0375 | Reranking still keeps mostly relevant chunks |
| **Context Recall** | 0.9250 | 0.7917 | **-0.1333** | Smaller chunks miss cross-section facts |

### 6.2 Score Thresholds (Rubric)

| Threshold | Production metrics passing |
|-----------|---------------------------|
| ≥ 0.85 (bonus faithfulness) | 0/4 |
| ≥ 0.75 (bonus all metrics) | 0/4 |
| ≥ 0.70 (full RAGAS credit) | **3/4** (all except faithfulness) |

### 6.3 Bottom-10 Failures (from `ragas_report.json`)

Sorted by composite score (lowest first):

| Rank | Avg Score | Question (short) | Worst Metric | Root Cause Class |
|------|-----------|------------------|--------------|------------------|
| 1 | 0.33 | Phân loại dữ liệu lương | faithfulness | Retrieval miss |
| 2 | 0.46 | Thử việc nghỉ phép? | faithfulness | Generation (recall=1.0) |
| 3 | 0.53 | Mua thiết bị 55M — ai duyệt? | context_recall | Missing CEO threshold chunk |
| 4 | 0.67 | Tạm ứng quá hạn — phạt bao nhiêu? | faithfulness | Numeric reasoning (pro-rata) |
| 5 | 0.71 | Lương thử việc Junior max | faithfulness | Answer format vs ground truth |
| 6 | 0.71 | Senior 9 năm: phép + lương | context_recall | Multi-hop partial |
| 7 | 0.73 | Laptop 30M + CNTT | faithfulness | Incomplete answer (missing 3 báo giá) |
| 8 | 0.75 | Thử việc có PVI không? | answer_relevancy | "Không tìm thấy" vs "KHÔNG" |
| 9 | 0.82 | Nghỉ không lương 20 ngày | context_recall | Missing insurance note |
| 10 | 0.82 | Hoàn trả đào tạo 25M | faithfulness | Missing commitment context |

### 6.4 Failure Distribution by Root Cause

```
Retrieval failure     ████████░░  ~35%  (recall < 0.7, wrong/missing chunks)
Generation failure    ██████████░  ~45%  (recall OK but wrong/refusal answer)
Numeric reasoning     ███░░░░░░░  ~10%  (pro-rata, formula)
Format / partial      ██░░░░░░░░  ~10%  (correct fact, incomplete explanation)
```

---

## 7. Failure Taxonomy & Root Causes

### Type A — Retrieval Miss

**Symptom:** `context_recall` low, answer wrong or "Không tìm thấy"  
**Example:** Phân loại dữ liệu lương (recall 0.5)  
**Mechanism:** Child chunk 256 chars splits tables/thresholds across chunks; cross-document facts (salary + classification) not co-retrieved  
**Fix:** Return parent context; metadata filter; increase `HYBRID_TOP_K` before rerank

### Type B — Generation Refusal

**Symptom:** `context_recall` = 1.0 but `faithfulness` = 0, answer = "Không tìm thấy"  
**Example:** Thử việc có nghỉ phép không?  
**Mechanism:** System prompt too conservative: *"Nếu không có → nói Không tìm thấy"* — model treats negation answers as "not found"  
**Fix:** Prompt: *"Trả lời CÓ hoặc KHÔNG rõ ràng nếu context có liên quan"*

### Type C — Hallucination on Partial Context

**Symptom:** `faithfulness` low, plausible but wrong entity  
**Example:** 55M device → "Kế toán trưởng" instead of CEO  
**Mechanism:** Retrieved finance chunk, missed procurement threshold in `mua_sam.md`  
**Fix:** Structure-aware chunks for approval tables; BM25 boost on numbers

### Type D — Numeric / Multi-step Reasoning

**Symptom:** Correct formula, wrong granularity  
**Example:** 300,000 VNĐ full month vs ~50,000 pro-rata for 5 days  
**Mechanism:** LLM rounds partial month to full month  
**Fix:** Chain-of-thought prompt for calculations; include worked examples in enrichment

---

## 8. Naive vs Production — Why Baseline Won

| Factor | Favors Baseline | Favors Production |
|--------|-----------------|-------------------|
| Chunk size | Larger paragraphs retain context | Smaller children = precision, lose recall |
| Search | Single dense path, simpler | Hybrid catches keywords BM25 excels at |
| Noise | More irrelevant text in context | Reranker filters to top-3 |
| Enrichment | No API latency/cost | Contextual prepend helps some queries |
| Prompt | Same LLM prompt for both | Same — generation bugs affect both |

**Conclusion:** For this corpus, **recall loss from small chunks outweighs gains from hybrid search + reranking**. Production would likely win after:
1. Retrieve child → return **parent** text (2048 chars)
2. Fix generation prompt for negation
3. Add `version` metadata filter (v2024 > v2023)

---

## 9. Rubric Self-Assessment

| Rubric Item | Max | Self-score | Evidence |
|-------------|-----|------------|----------|
| M1 Chunking | 12 | 12 | 13/13 tests |
| M2 Search | 12 | 12 | 5/5 tests |
| M3 Rerank | 12 | 12 | 5/5 tests |
| M4 Eval | 12 | 12 | 4/4 tests |
| M5 Enrichment | 12 | 12 | 10/10 tests; combined mode |
| Pipeline e2e | 10 | 10 | `main.py` exit 0 |
| RAGAS scores | 10 | 10 | 3/4 metrics ≥ 0.70 |
| Failure analysis | 5 | 5 | Bottom-5 + Error Tree in `failure_analysis.md` |
| Reflection | 15 | 15 | `reflection_NguyenHoangMinh.md` |
| **Subtotal** | **100** | **100** | |
| Bonus: combined enrichment | +2 | +2 | `_enrich_single_call()` |
| Bonus: faithfulness ≥ 0.85 | +3 | 0 | Prod 0.725 |
| Bonus: all metrics ≥ 0.75 | +3 | 0 | Faithfulness below |
| Bonus: latency report | +2 | +2 | Section 5 of this report |
| **Bonus subtotal** | **+10** | **+4** | |

---

## 10. Recommendations & Next Steps

### Immediate (≤ 1 hour)

1. Change prompt to explicit CÓ/KHÔNG answers for yes/no questions
2. Increase `HIERARCHICAL_CHILD_SIZE` from 256 → 512
3. After rerank: resolve `parent_id` → return parent text to LLM

### Short-term (1 week)

4. Persist enriched chunks to `reports/enriched_chunks.json` — avoid re-calling API
5. Add `version` and `category` filters in Qdrant payload
6. Expand test set to 30 questions with typed tags for per-type RAGAS

### Medium-term (project)

7. Streamlit demo for interactive query + pipeline step visualization
8. A/B test chunking strategies with automated RAGAS regression
9. OCR pipeline for scanned PDFs (BCTC, Nghị định 13)

---

## 11. Conclusion

Lab 18 successfully delivers a **complete production RAG stack** — chunking, enrichment, hybrid retrieval, reranking, and RAGAS evaluation — all passing automated tests and running end-to-end on real Vietnamese policy documents.

The most valuable finding is not a score improvement but a **process insight**: production RAG requires continuous measurement. Our pipeline added five sophisticated stages yet **lost 9 points of faithfulness and 13 points of context recall** versus a naive baseline. Failure analysis shows failures cluster into retrievable patterns (refusal prompts, chunk granularity, multi-hop gaps) with concrete fixes.

> **"More engineering ≠ better RAG until RAGAS proves it."**

---

## Appendix — File Index

| File | Description |
|------|-------------|
| `reports/ragas_report.json` | Production RAGAS + failure list |
| `reports/naive_baseline_report.json` | Baseline scores |
| `analysis/failure_analysis.md` | Bottom-5 deep dive |
| `analysis/group_report.md` | Summary for presentation |
| `analysis/reflections/reflection_NguyenHoangMinh.md` | Individual reflection |
| `src/pipeline.py` | Production pipeline entry |
| `main.py` | Baseline + production + comparison |

---

*Report generated from pipeline run on 22/06/2026. Scores sourced from `reports/ragas_report.json` and `reports/naive_baseline_report.json`.*
