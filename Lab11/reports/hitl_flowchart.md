# VinBank HITL Workflow — Flowchart & Decision Points

This document satisfies the **Lab 11 deliverable: HITL Flowchart** with three decision points and escalation paths. Diagrams use [Mermaid](https://mermaid.js.org/) (renders on GitHub, VS Code, and in the Streamlit Overview page).

---

## 1. End-to-End Pipeline + HITL Integration

```mermaid
flowchart TD
    A[Customer Message] --> B{Rate Limit OK?}
    B -->|No| Z1[Block: Wait and retry]
    B -->|Yes| C{Input Guardrails}
    C -->|Injection / Off-topic| Z2[Block: Banking-only message]
    C -->|Pass| D[VinBank LLM Agent]
    D --> E{Output Content Filter}
    E -->|Secrets/PII found| F[Redact sensitive data]
    E -->|Clean| G[Response text]
    F --> G
    G --> H{Multi-Criteria LLM Judge}
    H -->|FAIL| Z3[Block: Safe fallback message]
    H -->|PASS| I{Confidence Router}
    I -->|High risk action| J[HITL: Escalate immediately]
    I -->|Low confidence < 0.7| J
    I -->|Medium 0.7–0.9| K[HITL: Queue for review]
    I -->|High confidence ≥ 0.9| L[Auto-send to customer]
    J --> M[Human Reviewer]
    K --> M
    M -->|Approve| L
    M -->|Edit / Reject| N[Send revised or denial]
    L --> O[Audit Log]
    N --> O
    Z1 --> O
    Z2 --> O
    Z3 --> O
```

---

## 2. Confidence Router (TODO 12)

```mermaid
flowchart TD
    R[Agent Response + Metadata] --> A{Action type in HIGH_RISK list?}
    A -->|Yes: transfer, close account, etc.| E[ESCALATE — Priority HIGH — Human required]
    A -->|No| B{Confidence score}
    B -->|≥ 0.9| C[AUTO-SEND — Priority LOW]
    B -->|0.7 – 0.89| D[QUEUE REVIEW — Priority NORMAL — Human required]
    B -->|< 0.7| E
```

**High-risk actions (always escalate):** `transfer_money`, `close_account`, `change_password`, `delete_data`, `update_personal_info`

---

## 3. Decision Point 1 — Large Money Transfer

**Model:** Human-in-the-loop (human must approve before execution)

```mermaid
flowchart LR
    subgraph DP1[Decision Point 1: Large Transfer]
        T1[Customer requests transfer] --> T2{Amount > 50M VND?}
        T2 -->|No| T3[Agent may proceed if confident]
        T2 -->|Yes| T4[Agent prepares draft only]
        T4 --> T5[Human bank officer reviews]
        T5 --> T6{Approved?}
        T6 -->|Yes| T7[Execute transfer]
        T6 -->|No| T8[Reject / request more info]
    end
```

| Field | Value |
|-------|-------|
| **Trigger** | Transfer amount > 50,000,000 VND or exceeds daily limit |
| **Context for human** | Customer ID, balance, transfer history, beneficiary details, fraud score, device/location |
| **Example** | 100M VND to a new beneficiary — officer verifies beneficiary before release |
| **SLA** | < 5 minutes during business hours |

---

## 4. Decision Point 2 — Suspicious Account Activity

**Model:** Human-as-tiebreaker (agent proposes; human breaks deadlock)

```mermaid
flowchart LR
    subgraph DP2[Decision Point 2: Fraud Alert]
        F1[Customer reports unauthorized activity] --> F2{Agent confidence ≥ 0.7?}
        F2 -->|Yes| F3[Agent responds: freeze card / dispute steps]
        F2 -->|No| F4[Queue to fraud specialist]
        F4 --> F5[Human reviews logs + agent draft]
        F5 --> F6[Human selects final action]
        F6 --> F7[Freeze account / escalate police / gather info]
    end
```

| Field | Value |
|-------|-------|
| **Trigger** | Confidence < 0.7 on fraud-related query, or explicit unauthorized transaction report |
| **Context for human** | Transaction log, login history, IP addresses, prior fraud cases, agent proposal |
| **Example** | "Someone transferred 20M last night" — specialist decides freeze vs investigation |
| **SLA** | < 2 minutes (fraud urgency) |

---

## 5. Decision Point 3 — Loan Application

**Model:** Human-on-the-loop (agent drafts; human has final authority)

```mermaid
flowchart LR
    subgraph DP3[Decision Point 3: Loan Application]
        L1[Customer applies for loan] --> L2{Amount > 500M or borderline credit?}
        L2 -->|No| L3[Agent may auto-respond with standard info]
        L2 -->|Yes| L4[Agent drafts recommendation]
        L4 --> L5[Loan officer reviews package]
        L5 --> L6{Final decision}
        L6 -->|Approve| L7[Offer terms to customer]
        L6 -->|Reject| L8[Explain denial with compliance wording]
        L6 -->|More info| L9[Request documents]
    end
```

| Field | Value |
|-------|-------|
| **Trigger** | Loan > 500M VND, borderline credit score, or ambiguous income docs |
| **Context for human** | Credit report, income docs, employment verification, DTI ratio, agent recommendation |
| **Example** | 800M VND renovation loan with borderline score — officer makes final call |
| **SLA** | < 24 hours |

---

## 6. Escalation Summary Table

| Priority | Path | Who | Typical SLA |
|----------|------|-----|-------------|
| **Critical** | High-risk action or fraud | Fraud / senior officer | < 2 min |
| **High** | Low confidence (< 0.7) | Support specialist | < 5 min |
| **Normal** | Medium confidence (0.7–0.9) | Review queue | < 15 min |
| **Low** | High confidence (≥ 0.9), low risk | None — auto-send | Immediate |

---

## How to View

- **GitHub / VS Code:** Open this `.md` file — Mermaid renders in preview.
- **Streamlit:** See **Part 4: HITL Design** page for interactive router table.
- **Export PNG:** Use [mermaid.live](https://mermaid.live) — paste any diagram block.
