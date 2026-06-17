from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    min_rows = 5
    min_summary_chars = 20

    checks: list[dict[str, Any]] = [
        {
            "name": "row_count",
            "passed": len(df) >= min_rows,
            "value": int(len(df)),
            "threshold": min_rows,
        },
        {
            "name": "paper_id_not_null",
            "passed": bool(df["paper_id"].notna().all()) if len(df) else False,
            "value": int(df["paper_id"].notna().sum()) if len(df) else 0,
        },
        {
            "name": "paper_id_unique",
            "passed": bool(df["paper_id"].nunique() == len(df)) if len(df) else False,
            "value": int(df["paper_id"].nunique()) if len(df) else 0,
        },
        {
            "name": "title_not_null",
            "passed": bool(df["title"].notna().all()) if len(df) else False,
            "value": int(df["title"].notna().sum()) if len(df) else 0,
        },
        {
            "name": "summary_length",
            "passed": bool((df["summary_chars"] >= min_summary_chars).all()) if len(df) else False,
            "value": int((df["summary_chars"] >= min_summary_chars).sum()) if len(df) else 0,
            "threshold": min_summary_chars,
        },
        {
            "name": "freshness_threshold",
            "passed": bool((df["age_days"] <= settings.freshness_threshold_days).all())
            if len(df) and df["age_days"].notna().any()
            else False,
            "value": int((df["age_days"] <= settings.freshness_threshold_days).sum())
            if len(df)
            else 0,
            "threshold_days": settings.freshness_threshold_days,
        },
    ]

    report = {
        "report_name": report_name,
        "total_rows": int(len(df)),
        "checks": checks,
        "passed_checks": sum(1 for check in checks if check["passed"]),
        "failed_checks": sum(1 for check in checks if not check["passed"]),
        "success": all(check["passed"] for check in checks),
    }

    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if len(df) == 0:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False,
            "freshness_threshold_days": settings.freshness_threshold_days,
        }
        write_json(report_path, payload)
        return payload

    published_dates = pd.to_datetime(df["published"], errors="coerce").dropna()
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    payload = {
        "latest_published": published_dates.max().strftime("%Y-%m-%d") if len(published_dates) else None,
        "oldest_published": published_dates.min().strftime("%Y-%m-%d") if len(published_dates) else None,
        "stale_rows": stale_rows,
        "total_rows": int(len(df)),
        "is_fresh": stale_rows == 0,
        "freshness_threshold_days": settings.freshness_threshold_days,
    }
    write_json(report_path, payload)
    return payload
