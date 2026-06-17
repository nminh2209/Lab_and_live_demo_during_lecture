#!/usr/bin/env python3
"""Analyze run_output.json + logs — real metrics only."""
from __future__ import annotations
import base64
import glob
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = json.loads((ROOT / "run_output.json").read_text(encoding="utf-8"))
    results = out["results"]
    sealed = json.loads(base64.b64decode(out["sealed"]["data"]))

    log_files = sorted(glob.glob(str(ROOT / "logs" / "*.log")))
    rows = [json.loads(l) for l in open(log_files[-1], encoding="utf-8") if l.strip()] if log_files else []
    calls = [r for r in rows if r.get("event") == "AGENT_CALL"]

    lats = [c["data"].get("latency_ms") or 0 for c in calls]
    sl = sorted(lats)
    p95 = sl[int(0.95 * (len(sl) - 1))] if sl else 0

    report = {
        "n": len(results),
        "status": dict(Counter(r["status"] for r in results)),
        "latency_ms": {"p50": sl[len(sl) // 2] if sl else 0, "p95": p95, "max": max(lats) if lats else 0},
        "cost_usd": round(sum(c["data"].get("cost_usd", 0) for c in calls), 6),
        "tokens_total": sum(r["usage"]["total_tokens"] for r in sealed),
        "tools_avg": round(statistics.mean([len(r.get("tools_used") or []) for r in sealed]), 2),
        "pii_sealed": [results[i]["qid"] for i, r in enumerate(sealed) if r.get("pii")],
        "with_tong_cong": [r["qid"] for r in results if r.get("answer") and "tong cong" in r["answer"].lower()],
        "per_qid": [],
    }
    for i, r in enumerate(results):
        s = sealed[i]
        report["per_qid"].append({
            "qid": r["qid"],
            "status": r["status"],
            "pii": s.get("pii"),
            "steps": s.get("steps"),
            "tools": len(s.get("tools_used") or []),
            "latency_ms": s.get("latency_ms"),
            "has_total": bool(r.get("answer") and "tong cong" in (r.get("answer") or "").lower()),
        })

    out_path = ROOT / "final_metrics.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_qid"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
