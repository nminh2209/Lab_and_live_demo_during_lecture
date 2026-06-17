# Day 10 Lab — Detailed Technical Report
## Data Pipeline & Data Observability for Retrieval-Augmented Generation

**Project:** Day 10 — Data Pipeline and Data Observability  
**Date:** June 2026  
**Stack:** Python 3.13 · Crossref API · Pandas · MiniLM · ChromaDB · LangChain · OpenAI · Streamlit

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Objectives](#2-problem-statement--objectives)
3. [System Architecture](#3-system-architecture)
4. [Project Structure](#4-project-structure)
5. [Phase 1 — Baseline Pipeline](#5-phase-1--baseline-pipeline)
6. [Data Ingestion (Crossref)](#6-data-ingestion-crossref)
7. [Data Cleaning & Modeling](#7-data-cleaning--modeling)
8. [Embedding & Vector Store](#8-embedding--vector-store)
9. [Evaluation Framework](#9-evaluation-framework)
10. [RAG Agent & LLM Providers](#10-rag-agent--llm-providers)
11. [Data Observability](#11-data-observability)
12. [Corruption Experiment](#12-corruption-experiment)
13. [Results & Quantitative Analysis](#13-results--quantitative-analysis)
14. [Qualitative Failure Analysis](#14-qualitative-failure-analysis)
15. [Interactive Demo (Streamlit)](#15-interactive-demo-streamlit)
16. [Reproducibility Guide](#16-reproducibility-guide)
17. [Lessons Learned](#17-lessons-learned)
18. [Conclusion](#18-conclusion)

---

## 1. Executive Summary

This lab implements a **production-style RAG data pipeline** for scholarly papers. The system ingests academic metadata from the **Crossref REST API**, transforms it into a clean tabular corpus, embeds documents with **sentence-transformers/all-MiniLM-L6-v2**, indexes them in **ChromaDB**, and evaluates a factual question-answering layer over the corpus.

A second pipeline phase deliberately **corrupts** the clean dataset to simulate real-world data failures — missing records, blank fields, noisy text, truncated titles, stale publication dates, and duplicate rows. We measure the impact on retrieval and answer quality, then **repair** the dataset by re-processing from raw source records.

### Headline Results

| Stage | Retrieval Hit Rate | Mean Token F1 | Judge Accuracy | Quality Checks |
|-------|-------------------:|--------------:|---------------:|----------------|
| **Baseline** | 100% | 1.000 | 100% | 6/6 PASS |
| **Corrupted** | 62.5% | 0.568 | 58.3% | 3/6 PASS |
| **Repaired** | 100% | 1.000 | 100% | 6/6 PASS |

**Key takeaway:** Data quality is not a preprocessing nicety — it is a first-class dependency of RAG system reliability. Observability checks surfaced corruption before silent model degradation, and evaluation metrics quantified the business impact.

---

## 2. Problem Statement & Objectives

Modern LLM applications increasingly rely on **Retrieval-Augmented Generation (RAG)** to ground answers in external knowledge. However, a RAG system's accuracy depends on three interconnected layers:

1. **Data layer** — Is the source data complete, fresh, and deduplicated?
2. **Retrieval layer** — Can the vector index find the right document for a given question?
3. **Generation layer** — Does the model extract the correct fact from retrieved context?

This lab focuses on layers 1 and 2, with a lightweight generation layer for evaluation. The explicit goals were:

| # | Objective | Status |
|---|-----------|--------|
| 1 | Build an ETL pipeline from an external academic API | ✅ Complete |
| 2 | Clean and model data with a consistent schema | ✅ Complete |
| 3 | Create embeddings and a ChromaDB vector index | ✅ Complete |
| 4 | Build and evaluate a factual QA system | ✅ Complete |
| 5 | Implement data quality and freshness monitoring | ✅ Complete |
| 6 | Simulate corruption and measure downstream impact | ✅ Complete |
| 7 | Demonstrate repair from authoritative raw source | ✅ Complete |
| 8 | Provide reports and an interactive demo UI | ✅ Complete |

---

## 3. System Architecture

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                    PHASE 1 — BASELINE                     │
                    └──────────────────────────────────────────────────────────┘

  Crossref API          Raw JSON              Clean CSV           ChromaDB
 ┌───────────┐       ┌───────────┐         ┌───────────┐       ┌───────────┐
 │  /works   │──────▶│ crossref_ │────────▶│ papers_   │──────▶│ papers-   │
 │  endpoint │       │ records   │  clean  │ clean.csv │ embed │ baseline  │
 └───────────┘       └───────────┘         └───────────┘       └─────┬─────┘
                                                                     │
                    ┌────────────────────────────────────────────────┘
                    ▼
              ┌───────────┐       ┌───────────┐       ┌───────────┐
              │ Test Set  │──────▶│ QA Engine │──────▶│ Metrics & │
              │ (24 Qs)   │       │ top-k=4   │       │ Reports   │
              └───────────┘       └───────────┘       └───────────┘

                    ┌──────────────────────────────────────────────────────────┐
                    │              CORRUPTION FLOW                              │
                    └──────────────────────────────────────────────────────────┘

  Baseline CSV ──▶ Corrupt (6 ops) ──▶ Re-index ──▶ Re-evaluate ──▶ Compare
                         │                                              ▲
                         ▼                                              │
                   Raw records ──▶ Re-clean ──▶ Re-index ──▶ Re-evaluate ┘
                                  (repair)
```

### Design Principles

- **Separation of concerns:** ingestion, retrieval, evaluation, and observability live in distinct modules under `src/`.
- **Artifact-driven:** every pipeline stage writes inspectable outputs to `data/`.
- **Idempotent runs:** cached raw data and test sets can be reused via `REFRESH_SOURCE` / `REFRESH_TEST_SET` env flags.
- **Provider abstraction:** LLM calls go through a single `build_llm()` factory supporting six providers.

---

## 4. Project Structure

```
Day-10-Data-Pipeline-Data-Observability/
├── src/
│   ├── core/           # config.py, utils.py — paths, settings, I/O helpers
│   ├── ingestion/      # crossref.py, cleaning.py, corruption.py
│   ├── retrieval/      # embeddings.py, index.py, qa.py, agent.py, llm.py
│   ├── evaluation/     # testset.py, metrics.py
│   ├── observability/  # quality.py, reporting.py
│   └── pipelines/      # phase1.py, corruption_flow.py
├── script/
│   ├── run_phase1.py
│   └── run_corruption_flow.py
├── data/
│   ├── raw/            # API response + parsed records
│   ├── clean/          # baseline, corrupted, repaired datasets
│   ├── embeddings/     # ChromaDB manifests
│   ├── chroma/         # persistent vector store
│   ├── eval/           # test set
│   ├── results/        # metrics, answers, corruption log
│   ├── quality/        # quality + freshness JSON
│   └── reports/        # markdown reports
├── streamlit_app.py    # interactive demo UI
├── .env                # LLM_PROVIDER, OPENAI_API_KEY, etc.
└── Guide.md / Rubric.md
```

### Modules Implemented

| File | Responsibility |
|------|----------------|
| `src/ingestion/crossref.py` | Fetch, parse, persist Crossref records |
| `src/ingestion/cleaning.py` | Normalize schema, compute freshness, build `text_for_embedding` |
| `src/ingestion/corruption.py` | Apply six corruption operations with audit log |
| `src/evaluation/testset.py` | Generate typed evaluation questions |
| `src/observability/quality.py` | Row-level data quality checks |
| `src/observability/reporting.py` | Markdown report generation |
| `src/pipelines/phase1.py` | End-to-end baseline orchestration |
| `src/pipelines/corruption_flow.py` | Corrupt → evaluate → repair → compare |

Pre-built reference modules (`embeddings.py`, `index.py`, `qa.py`, `agent.py`, `llm.py`, `metrics.py`) were integrated rather than rewritten.

---

## 5. Phase 1 — Baseline Pipeline

The baseline pipeline (`script/run_phase1.py`) executes ten steps:

```
1. Load settings (.env + config.py paths)
2. Fetch raw records from Crossref (or load cached JSON)
3. Clean records → pandas DataFrame
4. Save clean CSV + JSON
5. Build ChromaDB index (collection: papers-baseline)
6. Build or load evaluation test set
7. Run evaluation (retrieval + QA + LLM judge)
8. Run data quality checks
9. Build freshness report
10. Generate markdown report + optional agent demo
```

### Configuration Highlights

| Setting | Value |
|---------|-------|
| Source API | Crossref REST API |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:<180 days ago>,has-abstract:true` |
| Max results | 24 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Top-k retrieval | 4 |
| Freshness threshold | 180 days |
| LLM provider | OpenAI (`gpt-4o-mini`) |

---

## 6. Data Ingestion (Crossref)

### API Integration

**Endpoint:** `https://api.crossref.org/works`

The fetcher builds query parameters from `Settings`, calls the API with retry logic for HTTP 429/503, and persists:

- `data/raw/crossref_response.json` — full API payload
- `data/raw/crossref_records.json` — parsed `PaperRecord` list

### Record Schema

```python
@dataclass
class PaperRecord:
    paper_id: str          # DOI
    title: str
    summary: str         # abstract (JATS XML stripped)
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str       # YYYY-MM-DD
    updated: str
    abs_url: str         # https://doi.org/{doi}
    pdf_url: str
    comment: str
```

### Parsing Logic

1. Iterate `payload["message"]["items"]`
2. Extract DOI, title, abstract, authors, subjects, dates, links
3. Strip JATS XML tags from abstracts (`<jats:p>`, etc.)
4. Normalize whitespace; skip records without DOI or title
5. Serialize to JSON for downstream loading

### Ingestion Results

| Metric | Value |
|--------|------:|
| API records fetched | 24 |
| Records after cleaning filter | 23 |
| Records dropped | 1 (missing/short abstract) |

---

## 7. Data Cleaning & Modeling

### Cleaning Rules

1. **Validity filter** — drop rows without `paper_id`, `title`, or summary < 20 characters
2. **Text normalization** — collapse whitespace in title, summary, authors, categories
3. **Date parsing** — parse `published` and `updated`; compute `age_days` from run date
4. **Helper columns:**
   - `authors_joined` — comma-separated author string
   - `categories_joined` — comma-separated category string
   - `summary_chars` — character count for quality checks
5. **Embedding text** — structured multi-field string:

```
Title: {title}
Authors: {authors_joined}
Categories: {categories_joined}
Summary: {summary}
```

6. **Deduplication** — keep first occurrence per `paper_id`
7. **Sort** — descending by `published` date

### Clean Dataset Snapshot

| Field | Example |
|-------|---------|
| `paper_id` | `10.21203/rs.3.rs-9882260/v1` |
| `title` | Operationalizing Reliability Gaps in Large Language Models… |
| `published` | 2026-06-02 |
| `age_days` | 8 |
| `summary_chars` | 1949 |

**Artifacts:** `data/clean/papers_clean.csv`, `papers_clean.json`

---

## 8. Embedding & Vector Store

### Embedding Model

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions:** 384
- **Normalization:** L2-normalized embeddings
- **Similarity:** cosine distance in ChromaDB HNSW index

### ChromaDB Collections

| Collection | Dataset | Manifest |
|------------|---------|----------|
| `papers-baseline` | Clean baseline | `data/embeddings/papers_embeddings.json` |
| `papers-corrupted` | Corrupted data | `data/embeddings/papers_embeddings_corrupted.json` |
| `papers-repaired` | Repaired data | `data/embeddings/papers_embeddings_repaired.json` |

Each document stores:
- `content` — the `text_for_embedding` string
- `metadata` — `paper_id`, `title`, `published`, `authors_joined`, `summary`, URLs

### Retrieval Modes

1. **Semantic search** — embed query, return top-k by cosine similarity
2. **Exact lookup** — match by `paper_id` or exact title (used when question contains quoted title)

---

## 9. Evaluation Framework

### Test Set Construction

Built from the top 8 most recently published papers in the clean corpus. For each paper, up to four question types are generated:

| Type | Question Pattern | Ground Truth Source |
|------|-----------------|---------------------|
| `summary` | "What is the main finding of the paper titled '…'?" | First sentence of summary |
| `authors` | "Who authored the paper '…'?" | `authors_joined` |
| `date` | "When was the paper '…' published?" | `published` |
| `categories` | "What categories apply to the paper '…'?" | `categories_joined` |

**Total evaluation samples:** 24 questions  
**Artifact:** `data/eval/test_set.json`

### Scoring Metrics

| Metric | Definition | Formula / Logic |
|--------|-----------|-----------------|
| **Retrieval hit rate** | Correct `paper_id` in top-k results | `mean(retrieval_hit)` |
| **Mean token F1** | Token overlap between answer and ground truth | Standard token-level F1 |
| **Judge accuracy** | LLM rates answer as materially correct | `mean(judge.correct)` |
| **Mean judge score** | Average 1–5 quality rating | `mean(judge.score)` |

The LLM judge uses structured output (`JudgeVerdict`) via OpenAI. A heuristic fallback (token F1 thresholds) activates if the LLM is unavailable.

### QA Answer Extraction

The QA layer (`src/retrieval/qa.py`) is rule-based for reproducibility:
- Author questions → return `authors_joined` from top result metadata
- Date questions → return `published`
- Category questions → return `categories_joined`
- Summary questions → return first sentence of `summary`

This design makes evaluation sensitive to **retrieval quality** — if the wrong document is retrieved, the answer will be wrong even without LLM hallucination.

---

## 10. RAG Agent & LLM Providers

### Agent Architecture

The LangChain agent (`src/retrieval/agent.py`) exposes two tools:

| Tool | Purpose |
|------|---------|
| `semantic_search_papers` | Embedding-based top-k search over the corpus |
| `lookup_paper` | Exact lookup by DOI or title |

The agent uses the configured LLM provider with a system prompt instructing it to use tools before answering factual questions.

### Supported LLM Providers

| Provider | Env Variable | Client |
|----------|-------------|--------|
| OpenAI | `OPENAI_API_KEY` | `ChatOpenAI` |
| Gemini | `GOOGLE_API_KEY` | `ChatGoogleGenerativeAI` |
| Anthropic | `ANTHROPIC_API_KEY` | `ChatAnthropic` |
| OpenRouter | `OPENROUTER_API_KEY` | `ChatOpenAI` (custom base URL) |
| Ollama | — | `ChatOllama` |
| Custom | `CUSTOM_LLM_BASE_URL` | `ChatOpenAI` (compatible endpoint) |

Configuration is driven by `.env`:
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

---

## 11. Data Observability

Data observability answers: **"Is our pipeline data healthy before we trust downstream models?"**

### Quality Checks (6 rules)

| Check | Rule | Baseline | Corrupted | Repaired |
|-------|------|:--------:|:---------:|:--------:|
| `row_count` | ≥ 5 rows | ✅ 23 | ✅ 22 | ✅ 23 |
| `paper_id_not_null` | All IDs present | ✅ | ✅ | ✅ |
| `paper_id_unique` | No duplicate IDs | ✅ | ❌ (20 unique / 22 rows) | ✅ |
| `title_not_null` | All titles present | ✅ | ✅ | ✅ |
| `summary_length` | All summaries ≥ 20 chars | ✅ | ❌ (19/22 pass) | ✅ |
| `freshness_threshold` | All `age_days` ≤ 180 | ✅ | ❌ (18/22 pass) | ✅ |

**Overall:** Baseline 6/6 · Corrupted 3/6 · Repaired 6/6

### Freshness Monitoring

| Field | Baseline | Corrupted | Repaired |
|-------|----------|-----------|----------|
| Latest published | 2026-06-02 | 2026-05-20 | 2026-06-02 |
| Oldest published | 2025-12-19 | **2010-01-01** | 2025-12-19 |
| Stale rows | 0 | **4** | 0 |
| Is fresh | ✅ True | ❌ False | ✅ True |

The corrupted dataset's stale dates (forced to 2010-01-01) and missing latest papers were immediately visible in observability reports — before anyone inspected model outputs.

---

## 12. Corruption Experiment

### Motivation

Production data pipelines fail in predictable ways: ETL jobs drop rows, fields get nullified, text gets corrupted, timestamps go stale, and deduplication breaks. This experiment injects six realistic failure modes to measure their compound effect on RAG performance.

### Operations Applied

| # | Operation | Count | Effect |
|---|-----------|------:|--------|
| 1 | **Drop latest records** | 3 | Remove newest papers by `published` date |
| 2 | **Blank summary** | 3 | Set `summary = ""`, `summary_chars = 0` |
| 3 | **Inject noise** | 4 | Append `[CORRUPTED NOISE xyz123]` to summaries |
| 4 | **Truncate title** | 3 | Cut titles to ~⅓ of original length |
| 5 | **Stale dates** | 4 | Set `published = 2010-01-01`, `age_days = 5000` |
| 6 | **Add duplicates** | 2 | Copy 2 random rows (breaks uniqueness) |

Dropped paper IDs:
- `10.21203/rs.3.rs-9882260/v1`
- `10.54254/2753-8818/2026.dl34055`
- `10.22214/ijraset.2026.82233`

After all operations, `text_for_embedding` is rebuilt to reflect the damaged content. A full audit log is written to `data/results/corruption_log.json`.

### Repair Strategy

Repair simulates a proper **source-of-truth re-sync**:

1. Load raw records from `data/raw/crossref_records.json`
2. Re-run the full cleaning pipeline (`build_clean_dataframe`)
3. Rebuild ChromaDB index (collection: `papers-repaired`)
4. Re-evaluate on the **same** test set (held constant to isolate data quality impact)

---

## 13. Results & Quantitative Analysis

### Evaluation Metrics

| Metric | Baseline | Corrupted | Δ (corrupt) | Repaired | Recovery |
|--------|----------|-----------|------------:|----------|----------|
| Retrieval hit rate | 1.000 | 0.625 | **−37.5%** | 1.000 | 100% |
| Mean token F1 | 1.000 | 0.568 | **−43.2%** | 1.000 | 100% |
| Judge accuracy | 1.000 | 0.583 | **−41.7%** | 1.000 | 100% |
| Mean judge score | 5.000 | 3.583 | **−28.3%** | 5.000 | 100% |

### Metric Degradation Chart (conceptual)

```
Retrieval Hit Rate
1.0 │ ████████████████████████████████ baseline
    │ ████████████████████             corrupted (62.5%)
    │ ████████████████████████████████ repaired
0.0 └────────────────────────────────────────────

Token F1
1.0 │ ████████████████████████████████ baseline
    │ ██████████████████               corrupted (56.8%)
    │ ████████████████████████████████ repaired
0.0 └────────────────────────────────────────────
```

### Impact by Corruption Type

| Failure Mode | Primary Impact |
|-------------|----------------|
| Drop latest records | **Retrieval miss** — correct paper no longer in index |
| Truncate titles | **Lookup failure** — exact title match in questions breaks |
| Blank summaries | **Answer degradation** — QA returns empty/wrong first sentence |
| Inject noise | **Semantic drift** — embeddings shift, wrong docs rank higher |
| Stale dates | **Observability alert** — freshness check fails |
| Duplicates | **Index pollution** — duplicate IDs, inconsistent retrieval |

---

## 14. Qualitative Failure Analysis

### Case Study: Dropped Paper

**Question:** *"What is the main finding of the paper titled 'Operationalizing Reliability Gaps in Large Language Models…'?"*

| Stage | Retrieved Top Doc | Retrieval Hit | Answer Quality |
|-------|-------------------|:-------------:|:--------------:|
| Baseline | Correct paper (`10.21203/...`) | ✅ | Token F1 = 1.0 |
| Corrupted | Wrong paper (`10.4018/...`) | ❌ | Token F1 = 0.32 |
| Repaired | Correct paper | ✅ | Token F1 = 1.0 |

**Root cause:** The target paper was among the 3 latest records dropped during corruption. Semantic search returned a topically similar but wrong RAG survey paper. The QA layer faithfully extracted the wrong paper's summary — demonstrating that **retrieval errors propagate directly to answers** even without LLM hallucination.

### Case Study: Truncated Title

A corrupted title like `"An Exploratory Study of Agentic Ret"` (truncated from full title) still appears in the index but can no longer be matched by exact title lookup in evaluation questions that use the full quoted title.

### Case Study: Noise Injection

Noise suffix `[CORRUPTED NOISE xyz123]` alters the embedding vector, causing semantically similar but incorrect documents to rank higher for some queries.

---

## 15. Interactive Demo (Streamlit)

A Streamlit application (`streamlit_app.py`) was built to showcase the lab interactively.

### Pages

| Page | Content |
|------|---------|
| **Overview** | Lab goals, pipeline flow diagram, core concept explanations (RAG, ETL, embeddings, observability, corruption) |
| **Pipeline Stages** | Step-by-step walkthrough with live artifact previews |
| **Metrics** | Bar charts comparing baseline / corrupted / repaired |
| **Observability** | Quality check pass/fail tables, freshness JSON |
| **Corruption** | Operations log, dataset size comparison, full comparison report |
| **Live Demo** | Ask questions against any corpus version; optional LLM agent |
| **Lab Report** | Renders this report in-browser |

### Launch

```bash
uv run streamlit run streamlit_app.py
```

Opens at `http://localhost:8501`.

---

## 16. Reproducibility Guide

### Prerequisites

- Python ≥ 3.13
- `uv` or `pip`
- OpenAI API key (for LLM judge and agent demo)

### Setup

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY

# 3. Run baseline pipeline
uv run python script/run_phase1.py

# 4. Run corruption experiment
uv run python script/run_corruption_flow.py

# 5. Launch interactive demo
uv run streamlit run streamlit_app.py
```

### Optional Environment Flags

| Variable | Effect |
|----------|--------|
| `REFRESH_SOURCE=1` | Re-fetch from Crossref API |
| `REFRESH_TEST_SET=1` | Regenerate evaluation questions |
| `RUN_RAGAS=1` | Enable slower Ragas evaluation pass |

### Output Artifacts Checklist

- [ ] `data/raw/crossref_response.json`
- [ ] `data/raw/crossref_records.json`
- [ ] `data/clean/papers_clean.csv`
- [ ] `data/embeddings/papers_embeddings.json`
- [ ] `data/eval/test_set.json`
- [ ] `data/results/baseline_metrics.json`
- [ ] `data/quality/baseline_quality.json`
- [ ] `data/reports/phase1_report.md`
- [ ] `data/results/corrupted_metrics.json`
- [ ] `data/results/repaired_metrics.json`
- [ ] `data/reports/corruption_report.md`

---

## 17. Lessons Learned

### 1. Data quality is a RAG prerequisite, not an afterthought
The corrupted pipeline passed 3/6 quality checks while retrieval hit rate dropped to 62.5%. Automated checks would have blocked deployment before users noticed wrong answers.

### 2. Retrieval errors dominate answer errors in this architecture
The QA layer is deterministic — it extracts facts from the top retrieved document. When retrieval fails, answers fail regardless of LLM capability.

### 3. Repair from source of truth works
Re-processing raw Crossref records fully restored all metrics. Production systems should always maintain an authoritative raw layer for re-sync.

### 4. Observability and evaluation are complementary
- **Observability** catches schema-level issues (duplicates, nulls, staleness)
- **Evaluation** catches semantic-level issues (wrong retrieval, wrong answers)
Together they provide defense in depth.

### 5. Hold test sets constant during corruption experiments
Using the same 24-question test set across baseline, corrupted, and repaired runs isolates the variable under study: data quality.

---

## 18. Conclusion

This lab successfully demonstrates a complete **data pipeline with observability** for a RAG system:

1. **Built** an ETL pipeline from Crossref → clean corpus → ChromaDB index
2. **Evaluated** factual QA with retrieval hit rate, token F1, and LLM judge scores
3. **Monitored** data health with six automated quality checks and freshness reporting
4. **Proved** that data corruption degrades RAG performance measurably (retrieval −37.5%, F1 −43.2%)
5. **Demonstrated** full recovery via source re-sync
6. **Delivered** markdown reports and an interactive Streamlit demo for presentation

The experiment validates a core principle for production AI systems: **invest in data pipeline observability with the same rigor as model evaluation**. A model can only be as reliable as the data it retrieves from.

---

## Appendix A — Rubric Self-Assessment

| Rubric Section | Max | Self-Score | Evidence |
|----------------|----:|:----------:|----------|
| Code structure & organization | 10 | 9 | Modular `src/` layout, clear naming |
| Raw data ingestion | 15 | 14 | Crossref fetch, parse, raw artifacts |
| Cleaning & data modeling | 15 | 14 | Schema, `text_for_embedding`, freshness |
| Embedding & vector store | 10 | 10 | MiniLM + ChromaDB, 3 collections |
| Agent & multi-provider LLM | 10 | 9 | 6 providers, tool-based agent |
| Evaluation & scoring | 10 | 10 | 24 samples, 4 metrics, answer artifacts |
| Data observability | 10 | 10 | 6 checks, freshness, reports |
| Corruption & comparison | 10 | 10 | 6 ops, measured impact, repair |
| **Total** | **90** | **~86–90** | |

---

## Appendix B — File Reference

| Report / Artifact | Path |
|-------------------|------|
| This detailed report | `data/reports/detailed_lab_report.md` |
| Phase 1 summary report | `data/reports/phase1_report.md` |
| Corruption comparison | `data/reports/corruption_report.md` |
| Baseline metrics | `data/results/baseline_metrics.json` |
| Corrupted metrics | `data/results/corrupted_metrics.json` |
| Repaired metrics | `data/results/repaired_metrics.json` |
| Corruption audit log | `data/results/corruption_log.json` |
| Streamlit demo | `streamlit_app.py` |
