# Lab 20 Submission — Multi-Agent Research System

**Course:** VinUniversity AI Lab · Phase 2 Day 5  
**Project:** `phase2-day5-multi-agent-lab`  
**Author:** Nguyen Hoang Minh  
**Date:** 2026-06-24  

---

## What this submission contains

This folder is the **official deliverable package** for Lab 20. Reviewers should start here, then read [`benchmark_report.md`](benchmark_report.md) for full metrics and evidence.

| Deliverable | File / link | Status |
|-------------|-------------|--------|
| Benchmark report (single vs multi-agent) | [`benchmark_report.md`](benchmark_report.md) | Included |
| Failure mode & mitigation | `benchmark_report.md` → § Failure mode observed | Included |
| Exit ticket (2 questions) | `benchmark_report.md` → § Exit ticket | Included |
| Peer review rubric self-score | `benchmark_report.md` → § Peer review rubric | **10/10** |
| LangSmith trace | [multi-agent-research-lab](https://smith.langchain.com/o/-/projects/p?name=multi-agent-research-lab) | _[Attach screenshot or paste run URL]_ |
| Source code | Repository root | _[Paste GitHub URL]_ |

---

## Results at a glance

**Primary query:** Research GraphRAG state-of-the-art and write a 500-word summary

| | Baseline | Multi-agent |
|---|:---:|:---:|
| Latency | 12.5s | 33.3s |
| Cost | $0.0005 | $0.0018 |
| Quality (LLM judge) | 8.0 / 10 | 8.0 / 10 |
| Citation coverage | 0% | 100% |
| Web sources (Tavily) | — | 5 |
| Suite failure rate (n=3) | 0% | 0% |

**Architecture:** LangGraph supervisor loop → Researcher (Tavily) → Analyst → Writer  
**Tracing:** LangSmith project `multi-agent-research-lab`

---

## Summary for reviewers

We built a production-style research assistant that compares **single-agent baseline** vs **multi-agent workflow** (Supervisor + Researcher + Analyst + Writer). Shared state lives in `ResearchState`; orchestration uses a compiled LangGraph graph; the Researcher calls **Tavily** for live sources; all runs export to **LangSmith**.

On the benchmark query, both modes scored **8.0/10** under an LLM peer-review judge. Multi-agent added **100% citation coverage** and five traceable Tavily sources at the cost of **~2.7× latency** and **~4× token cost**. Neither mode failed across the three-query evaluation suite.

**Strength:** Clear agent roles, auditable handoffs, real web search, and measurable benchmark with batch failure rate.  
**Trade-off:** Multi-agent is slower and more expensive; best when provenance and structure matter more than speed.

---

## Exit ticket (submission copy)

1. **When should you use multi-agent?**  
   When tasks need separated research, analysis, and writing phases with traceable artifacts and verifiable citations — e.g. technical research briefs or compliance-sensitive summaries.

2. **When should you not use multi-agent?**  
   When a single LLM call suffices: low-latency Q&A, cost-sensitive batch jobs, or simple transforms where citation provenance is not required.

---

## Peer review rubric — claimed score **10/10**

| Criterion | Pts | One-line evidence |
|-----------|----:|-------------------|
| Role clarity | 2 | Four agents, distinct outputs, minimal overlap |
| State design | 2 | `ResearchState` carries full handoff context |
| Failure guard | 2 | max iterations, timeout, retry, writer fallback |
| Benchmark | 2 | LLM judge + latency/cost/citations + 3-query failure rate |
| Trace explanation | 2 | LangSmith + per-agent trace and cost in state |

Detailed evidence and checklist: see [`benchmark_report.md`](benchmark_report.md).

---

## Items to complete before final hand-in

- [ ] Paste **GitHub repository URL** in the table above  
- [ ] Attach **LangSmith trace screenshot** or paste a specific run URL  
- [ ] Fill in **author name** at the top of this file  
- [ ] Confirm `reports/benchmark_report.md` is committed (not gitignored)

---

## Confidentiality note

API keys (`OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `TAVILY_API_KEY`) are stored in local `.env` only and are **not** part of this submission.
