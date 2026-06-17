# Nguyen Hoang Minh — final practice run

## Commands
```powershell
# Analyze metrics from run_output.json + logs
python harness/analyze_run.py

# Docker sim (Windows, custom endpoint)
$env:OPENAI_API_KEY="<custom_key>"
$env:OPENAI_BASE_URL="https://opencode.ai/zen/go/v1"
docker run --rm -e OPENAI_API_KEY -e OPENAI_BASE_URL -v "e:\VinAI\Day-13-Lab-Observathon:/lab" python:3.12-slim bash -c "cd /lab && chmod +x bin/practice/observathon-sim && ./bin/practice/observathon-sim --config solution/config.deepseek.json --wrapper solution/wrapper.py --out run_output.json --concurrency 4"
```

## Final metrics (2026-06-15)
- 20/20 ok, 0 max_steps
- latency p50=7627ms p95=16878ms max=92234ms
- cost $1.003686, 869746 tokens
- tools avg 2.20 max 3
- 20 traces in traces/traces.jsonl
- 5/20 answers contain `Tong cong:` line

## Remaining risks (honest)
- `self_consistency=2` caused one 92s request (cost/latency tradeoff)
- `quality_drift` / `prompt_injection` not tested (need multi-turn / private phase)
- `score.json` unavailable — no observathon-score in GitHub release
- `solution/config.json` is set to `gpt-4o-mini` for OpenAI cost control; this measured run used temporary `solution/config.deepseek.json`
