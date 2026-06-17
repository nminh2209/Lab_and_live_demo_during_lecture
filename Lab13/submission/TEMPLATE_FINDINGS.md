# Findings — Nguyen Hoang Minh

Evidence: **baseline** = first Docker run (shipped config). **After fix** = latest real Docker run (`run_output.json` 2026-06-15) via custom OpenAI-compatible endpoint.

## Final run results (real, measured)

| Metric | Value | Source |
|--------|-------|--------|
| Requests | 20 | run_output.json |
| Status | **20 ok**, 0 max_steps | run_output.json |
| Latency p50 / p95 / max | **7627 / 16878 / 92234 ms** | logs AGENT_CALL |
| Cost | **$1.003686** | logs AGENT_CALL |
| Tokens | **869,746** | sealed block |
| Tools per call avg / max | **2.20 / 3** | sealed |
| PII in wrapper logs | **0** | AGENT_CALL |
| Traces exported | **20** | traces/traces.jsonl |
| Answers with `Tong cong` | **5/20** | run_output.json |

## Baseline → after comparison

| Metric | Baseline (shipped config) | After fix |
|--------|---------------------------|-----------|
| ok / max_steps | 16 / 4 | **20 / 0** |
| latency p95 | 25,627 ms | **16,878 ms** |
| tools avg | 4.0 | **2.20** |
| PII leaks | 2/20 | **2/20 (sealed flags remain: prac-010, prac-013)** |

## Faults diagnosed & fixes applied

| fault_class | baseline evidence | fix |
|---|---|---|
| infinite_loop | 4/20 max_steps; prac-003 ×12 check_stock | loop_guard, tool_budget |
| error_spike | 20% failures | retry, lower tool_error_rate |
| latency_spike | p95 25.6s | verbose off, loops stopped |
| cost_blowup | 437k tokens, loops | standard tier, tool_budget |
| pii_leak | prac-010, prac-013 phones | redact_pii + wrapper sanitize (residual sealed flags remain) |
| tool_overuse | max 13 tools | tool_budget=4, temp 0.2 |
| tool_failure | unicode/shipping fails | normalize_unicode=true |

## Lab deliverables

| Item | Status |
|------|--------|
| `solution/config.json` optimized (`gpt-4o-mini`) | Done |
| `solution/prompt.txt` rewritten | Done (1353 chars) |
| `solution/wrapper.py` observability + mitigations | Done |
| Practice sim via Docker | Done |
| `run_output.json` | Done |
| `logs/` + `traces/traces.jsonl` | Done |
| `findings.json` | Done |
| `score.json` | N/A — scorer binary not in release |

## Model and endpoint note

- `solution/config.json` now uses `gpt-4o-mini` (to reduce OpenAI spend).
- This specific final run used a temporary config (`solution/config.deepseek.json`) with model `deepseek-v4-flash`
  on endpoint `https://opencode.ai/zen/go/v1` because that endpoint rejected `gpt-4o-mini` as unsupported.

## Re-run command

```powershell
$env:OPENAI_API_KEY="<custom_key>"
$env:OPENAI_BASE_URL="https://opencode.ai/zen/go/v1"
docker run --rm -e OPENAI_API_KEY -e OPENAI_BASE_URL `
  -v "e:\VinAI\Day-13-Lab-Observathon:/lab" `
  python:3.12-slim `
  bash -c "cd /lab && chmod +x bin/practice/observathon-sim && ./bin/practice/observathon-sim --config solution/config.deepseek.json --wrapper solution/wrapper.py --out run_output.json --concurrency 4"
```
