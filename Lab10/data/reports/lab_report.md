# Day 10 Lab Report: Data Pipeline & Data Observability for RAG

## Executive Summary

This lab builds an end-to-end **Retrieval-Augmented Generation (RAG)** data pipeline for scholarly papers. Data is ingested from the **Crossref REST API**, cleaned into a structured corpus, embedded with **MiniLM**, indexed in **ChromaDB**, and evaluated with a factual QA system. We then simulate **data corruption**, measure its impact on retrieval and answer quality, and demonstrate **repair** by re-processing from raw source records.

The experiment confirms a core observability insight: **downstream RAG performance is only as good as upstream data quality**. Corruption degraded retrieval hit rate from **100% → 62.5%** and mean token F1 from **1.0 → 0.57**; repair restored all metrics to baseline.

---

## 1. Objectives

| Goal | Description |
|------|-------------|
| ETL pipeline | Fetch, parse, clean, and persist academic paper metadata |
| Vector store | Embed documents and enable semantic search via ChromaDB |
| RAG agent | Answer factual questions using retrieval + LLM tools |
| Evaluation | Score retrieval accuracy, token overlap, and LLM judge quality |
| Observability | Monitor data quality, freshness, and pipeline health |
| Corruption study | Simulate realistic data failures and measure recovery |

---

## 2. System Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Crossref   │───▶│  Ingestion   │───▶│  Cleaning &     │───▶│  Embedding   │
│  REST API   │    │  (raw JSON)  │    │  Modeling       │    │  (MiniLM)    │
└─────────────┘    └──────────────┘    └─────────────────┘    └──────┬───────┘
                                                                      │
                    ┌──────────────┐    ┌─────────────────┐          ▼
                    │  Evaluation  │◀───│  RAG QA / Agent │◀─── ChromaDB
                    │  & Metrics   │    │  (retrieval)    │
                    └──────┬───────┘    └─────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌─────────────────┐      ┌─────────────────┐
     │ Data Quality    │      │ Freshness       │
     │ Checks          │      │ Monitoring      │
     └─────────────────┘      └─────────────────┘
```

**Two pipeline phases:**

1. **Phase 1 (Baseline)** — clean data → index → evaluate → report
2. **Corruption Flow** — corrupt → re-evaluate → repair from raw → compare

---

## 3. Data Ingestion

### Source

- **API:** Crossref REST API (`https://api.crossref.org/works`)
- **Query:** `agentic retrieval augmented generation large language model`
- **Filter:** `from-pub-date:<180 days ago>,has-abstract:true`
- **Max results:** 24 papers

### Record Schema (`PaperRecord`)

| Field | Description |
|-------|-------------|
| `paper_id` | DOI (unique identifier) |
| `title` | Paper title |
| `summary` | Abstract (JATS XML stripped) |
| `authors` | List of author names |
| `categories` | Subject tags from Crossref |
| `published` / `updated` | Publication and index dates |
| `abs_url` / `pdf_url` | DOI and PDF links |

### Artifacts

- `data/raw/crossref_response.json` — full API response
- `data/raw/crossref_records.json` — parsed records

**Results:** 24 raw records fetched; 23 passed cleaning filters.

---

## 4. Cleaning & Data Modeling

Cleaning rules applied:

1. Drop records without `paper_id`, `title`, or summary &lt; 20 characters
2. Normalize whitespace in text fields
3. Parse dates and compute `age_days` relative to pipeline run date
4. Build helper columns: `authors_joined`, `categories_joined`, `summary_chars`
5. Construct `text_for_embedding` for vector indexing:

```
Title: {title}
Authors: {authors_joined}
Categories: {categories_joined}
Summary: {summary}
```

6. Deduplicate by `paper_id`, sort by `published` descending

**Artifacts:** `data/clean/papers_clean.csv`, `papers_clean.json`

---

## 5. Embedding & Vector Store

- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, cosine similarity)
- **Store:** ChromaDB persistent client at `data/chroma/`
- **Collections:** `papers-baseline`, `papers-corrupted`, `papers-repaired`

Each document is indexed with metadata (`paper_id`, `title`, `published`, `authors_joined`, `summary`, etc.) enabling both semantic search and exact lookup by ID/title.

---

## 6. Evaluation Methodology

### Test Set

Built from the cleaned corpus with four question types:

| Type | Example pattern |
|------|-----------------|
| `summary` | "What is the main finding of the paper titled '...'?" |
| `authors` | "Who authored the paper '...'?" |
| `date` | "When was the paper '...' published?" |
| `categories` | "What categories apply to the paper '...'?" |

Each sample includes `ground_truth` and `ground_truth_doc_ids` for scoring.

### Metrics

| Metric | Meaning |
|--------|---------|
| **Retrieval hit rate** | Fraction of questions where the correct `paper_id` appears in top-k results |
| **Mean token F1** | Token-level overlap between predicted and reference answers |
| **Judge accuracy** | LLM judge (or heuristic fallback) rates answer as materially correct |
| **Mean judge score** | Average 1–5 quality score from the judge |

**Artifacts:** `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/results/*_answers.json`

---

## 7. Data Observability

### Quality Checks

| Check | Rule |
|-------|------|
| `row_count` | ≥ 5 documents |
| `paper_id_not_null` | All IDs present |
| `paper_id_unique` | No duplicate IDs |
| `title_not_null` | All titles present |
| `summary_length` | All summaries ≥ 20 chars |
| `freshness_threshold` | All `age_days` ≤ 180 |

### Freshness Monitoring

Tracks `latest_published`, `oldest_published`, `stale_rows`, and `is_fresh` against the 180-day threshold.

**Baseline:** 6/6 checks passed, 0 stale rows  
**Corrupted:** 3/6 checks failed (duplicates, short summaries, stale dates)  
**Repaired:** 6/6 checks passed, 0 stale rows

---

## 8. Corruption Experiment

Six corruption operations were applied to the baseline dataset:

| Operation | Effect |
|-----------|--------|
| Drop latest records | Remove 3 most recently published papers |
| Blank summary | Clear abstract text on 3 rows |
| Inject noise | Append `[CORRUPTED NOISE xyz123]` to 4 summaries |
| Truncate title | Cut titles to ~⅓ length on 3 rows |
| Stale dates | Set `published` to 2010-01-01 on 4 rows |
| Add duplicates | Copy 2 random rows (breaks uniqueness) |

After corruption, `text_for_embedding` was rebuilt to reflect damaged content.

### Repair Strategy

Re-load raw records from `data/raw/crossref_records.json` and re-run the full cleaning pipeline — simulating a proper ETL re-sync from source of truth.

---

## 9. Results

### Evaluation Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
|--------|----------|-----------|----------|
| Retrieval hit rate | 1.000 | 0.625 | 1.000 |
| Mean token F1 | 1.000 | 0.568 | 1.000 |
| Judge accuracy | 1.000 | 0.542 | 1.000 |
| Mean judge score | 5.000 | 3.167 | 5.000 |

### Key Findings

1. **Dropping papers and truncating titles** reduced retrieval hit rate — the correct document was no longer findable for some test questions.
2. **Blank/noisy summaries** degraded answer extraction — token F1 dropped because the QA layer reads summary metadata from the top retrieved result.
3. **Stale dates and duplicates** failed observability checks, surfacing data health issues before they silently poison downstream models.
4. **Repair from raw source** fully restored both data quality checks and evaluation metrics.

---

## 10. Agent & Multi-Provider LLM

The RAG agent (`src/retrieval/agent.py`) exposes two tools:

- `semantic_search_papers` — embedding-based top-k retrieval
- `lookup_paper` — exact match by DOI or title

LLM providers supported via `src/retrieval/llm.py`: OpenAI, Gemini, Anthropic, OpenRouter, Ollama, and custom OpenAI-compatible endpoints. Configuration is driven by `.env` (`LLM_PROVIDER`, `LLM_MODEL`, API keys).

---

## 11. Artifacts Index

| Path | Contents |
|------|----------|
| `data/raw/` | Raw API response and parsed records |
| `data/clean/` | Baseline, corrupted, and repaired datasets |
| `data/embeddings/` | ChromaDB manifests per collection |
| `data/chroma/` | Persistent vector store |
| `data/eval/` | Evaluation test set |
| `data/results/` | Metrics, answers, corruption log |
| `data/quality/` | Quality check JSON reports |
| `data/reports/` | Markdown reports (phase1, corruption, this report) |

---

## 12. How to Reproduce

```bash
uv sync
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run streamlit run streamlit_app.py
```

Set `OPENAI_API_KEY` in `.env` for LLM judge and agent demo.

---

## 13. Conclusion

This lab demonstrates that a RAG system requires **three layers of quality assurance**:

1. **Ingestion quality** — valid schema, complete fields, deduplication
2. **Pipeline observability** — automated checks on freshness, uniqueness, and completeness
3. **Downstream evaluation** — retrieval and answer metrics that detect silent degradation

When data corruption occurs, observability checks flag the problem early, and evaluation metrics quantify the business impact. Repairing from the authoritative raw source restores system trust — a pattern every production data pipeline should support.
