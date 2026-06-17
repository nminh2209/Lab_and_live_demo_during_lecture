# Phase 1 Baseline Report

## Source Summary
- **API**: Crossref REST API
- **Query**: agentic retrieval augmented generation large language model
- **Filter**: from-pub-date:2025-12-12,has-abstract:true
- **Raw records**: 24
- **Clean records**: 23

## Evaluation Metrics
- **Samples**: 24
- **Retrieval hit rate**: 1.0000
- **Mean token F1**: 1.0000
- **Judge accuracy**: 1.0000
- **Mean judge score**: 5

## Data Quality
- **Success**: True
- **Passed checks**: 6
- **Failed checks**: 0
  - `row_count`: PASS (value=23)
  - `paper_id_not_null`: PASS (value=23)
  - `paper_id_unique`: PASS (value=23)
  - `title_not_null`: PASS (value=23)
  - `summary_length`: PASS (value=23)
  - `freshness_threshold`: PASS (value=23)

## Freshness
- **Latest published**: 2026-06-02
- **Oldest published**: 2025-12-19
- **Stale rows**: 0
- **Total rows**: 23
- **Is fresh**: True
