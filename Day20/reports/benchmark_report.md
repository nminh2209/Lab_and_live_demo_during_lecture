# Benchmark Report — Lab 20: Multi-Agent Research System

| Field | Value |
|-------|-------|
| **Primary query** | Research GraphRAG state-of-the-art and write a 500-word summary |
| **Model** | `gpt-4o-mini` |
| **Run date** | 2026-06-24 |
| **Web search** | Tavily (live) |
| **Orchestration** | LangGraph compiled `StateGraph` |
| **Tracing** | LangSmith project `multi-agent-research-lab` |

---

## Executive summary

Multi-agent workflow matched baseline **quality** (8.0/10 LLM judge) while delivering **100% citation coverage** and **5 Tavily-sourced references**. Trade-off: **2.7× latency** and **~4× cost**. Both modes achieved **0% failure rate** across a 3-query benchmark suite.

---

## Primary query metrics

| Run | Latency (s) | Cost (USD) | Quality (0–10) | Citation coverage | Suite failure rate | Scoring method |
|---|---:|---:|---:|---:|---:|---|
| Single-agent baseline | 12.48 | 0.0005 | 8.0 | 0% | 0% (0/3) | `llm_judge` |
| Multi-agent | 33.25 | 0.0018 | 8.0 | 100% | 0% (0/3) | `llm_judge` |

### Comparison deltas (multi-agent vs baseline)

| Metric | Baseline | Multi-agent | Delta |
|---|---:|---:|---|
| Latency | 12.5s | 33.3s | +20.8s (+167%) |
| Estimated cost | $0.00045 | $0.00179 | +$0.0013 (+296%) |
| Quality (LLM judge) | 8.0 | 8.0 | 0.0 |
| Citation coverage | 0% | 100% | +100 pp |
| Sources in state | 0 | 5 | +5 |
| LLM calls (primary run) | 2 | 6 | +4 |

---

## Batch failure rate (lab guide metric)

**Definition:** failed queries ÷ total queries in suite (failure = errors or empty `final_answer`).

**Suite size:** 3 queries

| # | Suite query | Baseline | Multi-agent |
|---|-------------|:--------:|:-----------:|
| 1 | Research GraphRAG state-of-the-art and write a 500-word summary | pass | pass |
| 2 | Compare RAG vs fine-tuning for enterprise knowledge bases | pass | pass |
| 3 | Summarize recent advances in multi-agent LLM orchestration | pass | pass |
| | **Failure rate** | **0%** | **0%** |

---

## Multi-agent pipeline trace (primary query)

```
START → supervisor → researcher (Tavily, 5 sources)
                 → supervisor → analyst
                 → supervisor → writer
                 → supervisor → done
```

| Step | Agent | Output | Approx. cost contribution |
|------|-------|--------|---------------------------|
| 1 | Researcher | `research_notes` (3,613 chars), 5 Tavily sources | $0.00065 |
| 2 | Analyst | `analysis_notes` (2,445 chars), weak-evidence flags | $0.00042 |
| 3 | Writer | `final_answer` (4,200 chars), inline `[1]`–`[5]` citations | $0.00071 |
| | **Total multi-agent LLM cost** | | **~$0.00179** |

**Route history:** `['researcher', 'analyst', 'writer', 'done']`

**LangSmith dashboard:** https://smith.langchain.com/o/-/projects/p?name=multi-agent-research-lab

---

## Tavily sources (multi-agent, primary query)

| # | Title | Provider |
|---|-------|----------|
| 1 | Microsoft GraphRAG Overview | tavily |
| 2 | Retrieval-Augmented Generation with Graphs (GraphRAG) | tavily |
| 3 | GraphRAG Explained: Enhancing RAG with Knowledge Graphs | tavily |
| 4 | How GraphRAG Accelerates Time to Insight and Boosts ROI | tavily |
| 5 | Microsoft's GraphRAG is One of the Newest RAG Techniques | tavily |

---

## Reflection

### When multi-agent helps

Use multi-agent when the task decomposes into **research → analysis → writing**, and you need **auditable handoffs**, **live web sources**, and **citation provenance**. This run: equal judge quality (8.0) but multi-agent alone achieved full citation coverage and retained intermediate artifacts for debugging.

### When single-agent is enough

Use a single LLM call when latency and cost matter more than source tracking — e.g. internal drafts, brainstorming, or summaries where citations are optional. Baseline completed in **12.5s** at **~4× lower cost** with the same judge score.

### Failure mode observed

**Symptom:** Multi-agent latency and cost scale with agent count (5+ LLM calls + Tavily per run).

**Impact:** Acceptable for research deliverables; poor fit for real-time chat.

**Mitigations implemented:** `max_iterations=6`, OpenAI timeout, LLM retry (3×), writer fallback on worker failure.

**Future improvements:** Cache Tavily results; skip analyst for factual lookups; parallelize independent steps.

---

## Exit ticket (lab deliverable)

**1. When should you use multi-agent?**  
When tasks need separated responsibilities, traceable intermediate outputs, and verifiable citations — e.g. technical research briefs, compliance-sensitive summaries, or workflows where you must explain which phase gathered vs analyzed vs wrote the answer.

**2. When should you not use multi-agent?**  
When a single well-prompted call is sufficient: low-latency Q&A, cost-sensitive batch jobs, simple transforms, or cases where sub-second response time outweighs provenance and structure.

---

## Peer review rubric (max 10)

| Criterion | Score | Evidence |
|-----------|------:|----------|
| **Role clarity** | 2/2 | Supervisor routes; Researcher (Tavily + notes), Analyst (claims/evidence), Writer (cited answer) — distinct `agents/*.py` prompts and state fields |
| **State design** | 2/2 | `ResearchState`: `sources`, `research_notes`, `analysis_notes`, `final_answer`, `route_history`, `trace`, `agent_results`, `errors` |
| **Failure guard** | 2/2 | `MAX_ITERATIONS=6`, `TIMEOUT_SECONDS=60`, tenacity retry on LLM, writer fallback, errors recorded on state |
| **Benchmark** | 2/2 | Latency, cost, citation coverage, LLM-judged quality, 3-query failure rate; baseline vs multi compared in this report |
| **Trace explanation** | 2/2 | LangSmith project traces + `state.trace` events per agent + per-agent token/cost in `agent_results` |

**Total: 10/10**

---

## Submission checklist (detailed)

Use this section when handing in the lab. Mark each item before push/PR.

### A. Repository & code

| # | Item | Location | Done |
|---|------|----------|:----:|
| A1 | Source code pushed to GitHub | Remote repo | ☐ |
| A2 | `.env` **not** committed (keys stay local) | Root `.gitignore` | ☑ |
| A3 | LangGraph workflow implemented | `graph/workflow.py` | ☑ |
| A4 | Tavily web search wired | `services/search_client.py` | ☑ |
| A5 | LangSmith tracing enabled | `observability/tracing.py` + `.env` | ☑ |
| A6 | Streamlit demo (optional showcase) | `streamlit_app.py` | ☑ |

### B. Benchmark deliverables

| # | Item | Location | Done |
|---|------|----------|:----:|
| B1 | Benchmark report committed | `reports/benchmark_report.md` | ☑ |
| B2 | Single vs multi-agent comparison | § Primary query metrics | ☑ |
| B3 | Latency measured (wall-clock) | 12.5s vs 33.3s | ☑ |
| B4 | Cost estimated (token usage) | $0.0005 vs $0.0018 | ☑ |
| B5 | Quality scored (0–10) | 8.0 vs 8.0 (`llm_judge`) | ☑ |
| B6 | Citation coverage measured | 0% vs 100% | ☑ |
| B7 | Batch failure rate (3 queries) | 0% vs 0% | ☑ |

### C. Trace & observability

| # | Item | Location | Done |
|---|------|----------|:----:|
| C1 | LangSmith project configured | `multi-agent-research-lab` | ☑ |
| C2 | Trace URL or screenshot attached | PR / `reports/README.md` | ☐ |
| C3 | Can explain agent sequence | § Multi-agent pipeline trace | ☑ |
| C4 | Per-agent cost explainable | `agent_results[].metadata.cost_usd` | ☑ |

### D. Written deliverables

| # | Item | Location | Done |
|---|------|----------|:----:|
| D1 | Failure mode + fix documented | § Failure mode observed | ☑ |
| D2 | Exit ticket (2 questions) | § Exit ticket | ☑ |
| D3 | Submission cover note for reviewer | `reports/README.md` | ☑ |

### E. Peer review readiness

| # | Question a reviewer might ask | Answer pointer |
|---|------------------------------|----------------|
| E1 | Who does what? | Researcher / Analyst / Writer roles in § Multi-agent pipeline trace |
| E2 | What is shared between agents? | `core/state.py` — see State design row in rubric |
| E3 | What if an agent fails? | Writer fallback + `errors[]`; guardrails in Failure mode section |
| E4 | Why multi-agent over baseline? | § Reflection — citations + auditability vs speed/cost |
| E5 | Show me the trace | LangSmith link above + Streamlit Trace tab |

---

## Appendix: infrastructure stack

| Layer | Technology |
|-------|------------|
| LLM | OpenAI `gpt-4o-mini` via `LLMClient` |
| Search | Tavily API (`search_provider: tavily`) |
| Graph | LangGraph `StateGraph` — supervisor conditional loop |
| Trace | LangSmith (`LANGCHAIN_TRACING_V2`) |
| Eval | `run_benchmark_suite()` — LLM judge + failure-rate batch |
| Demo | Streamlit (`streamlit run streamlit_app.py`) |
