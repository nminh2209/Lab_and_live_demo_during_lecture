# Corruption Impact Report

## Metric Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.6250 | 1.0000 |
| Mean token F1 | 1.0000 | 0.5682 | 1.0000 |
| Judge accuracy | 1.0000 | 0.5833 | 1.0000 |
| Mean judge score | 5.0000 | 3.5833 | 5.0000 |

## Trend Summary
- Retrieval hit rate: 1.0000 -> 0.6250 -> 1.0000
- Mean token F1: 1.0000 -> 0.5682 -> 1.0000
- Judge accuracy: 1.0000 -> 0.5833 -> 1.0000
- Mean judge score: 5.0000 -> 3.5833 -> 5.0000

## Corrupted Data Quality
- **Success**: False
- **Passed checks**: 3
- **Failed checks**: 3
  - `row_count`: PASS (value=22)
  - `paper_id_not_null`: PASS (value=22)
  - `paper_id_unique`: FAIL (value=20)
  - `title_not_null`: PASS (value=22)
  - `summary_length`: FAIL (value=19)
  - `freshness_threshold`: FAIL (value=18)

## Repaired Data Quality
- **Success**: True
- **Passed checks**: 6
- **Failed checks**: 0
  - `row_count`: PASS (value=23)
  - `paper_id_not_null`: PASS (value=23)
  - `paper_id_unique`: PASS (value=23)
  - `title_not_null`: PASS (value=23)
  - `summary_length`: PASS (value=23)
  - `freshness_threshold`: PASS (value=23)

## Corrupted Freshness
- **Latest published**: 2026-05-20
- **Oldest published**: 2010-01-01
- **Stale rows**: 4
- **Total rows**: 22
- **Is fresh**: False

## Repaired Freshness
- **Latest published**: 2026-06-02
- **Oldest published**: 2025-12-19
- **Stale rows**: 0
- **Total rows**: 23
- **Is fresh**: True

## Conclusion
Corruption degrades retrieval and answer quality; repairing from the raw source restores metrics toward baseline.
