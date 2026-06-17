from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(value: str) -> pd.Timestamp | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.tz_localize(None) if getattr(parsed, "tzinfo", None) else parsed


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows: list[dict] = []
    run_ts = pd.Timestamp(run_date).tz_localize(None) if run_date.tzinfo else pd.Timestamp(run_date)

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(author) for author in record.authors if author]
        categories = [normalize_whitespace(category) for category in record.categories if category]
        primary_category = normalize_whitespace(record.primary_category) or (
            categories[0] if categories else "uncategorized"
        )

        if not record.paper_id or not title or len(summary) < 20:
            continue

        published_ts = _parse_date(record.published) or _parse_date(record.updated)
        published = published_ts.strftime("%Y-%m-%d") if published_ts is not None else ""
        updated_ts = _parse_date(record.updated) or published_ts
        updated = updated_ts.strftime("%Y-%m-%d") if updated_ts is not None else published
        age_days = int((run_ts - published_ts).days) if published_ts is not None else None

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        summary_chars = len(summary)
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": normalize_whitespace(record.comment),
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["summary_chars"] >= 20]
    df = df.sort_values(["published", "title"], ascending=[False, True]).reset_index(drop=True)
    return df
