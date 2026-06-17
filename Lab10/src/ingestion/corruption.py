from __future__ import annotations

import random

import pandas as pd

from core.utils import write_json


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    corrupted = df.copy()
    log: dict = {"operations": []}
    random.seed(42)

    drop_count = min(3, max(1, len(corrupted) // 5))
    latest_rows = corrupted.sort_values("published", ascending=False).head(drop_count)
    dropped_ids = latest_rows["paper_id"].tolist()
    corrupted = corrupted[~corrupted["paper_id"].isin(dropped_ids)].reset_index(drop=True)
    log["operations"].append({"type": "drop_latest_records", "count": drop_count, "paper_ids": dropped_ids})

    blank_indices = corrupted.sample(n=min(3, len(corrupted)), random_state=42).index
    for idx in blank_indices:
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0
    log["operations"].append({"type": "blank_summary", "count": len(blank_indices), "indices": blank_indices.tolist()})

    noise_indices = corrupted.sample(n=min(4, len(corrupted)), random_state=7).index
    for idx in noise_indices:
        corrupted.at[idx, "summary"] = f"{corrupted.at[idx, 'summary']} [CORRUPTED NOISE xyz123]"
        corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])
    log["operations"].append({"type": "inject_noise", "count": len(noise_indices), "indices": noise_indices.tolist()})

    truncate_indices = corrupted.sample(n=min(3, len(corrupted)), random_state=11).index
    for idx in truncate_indices:
        title = corrupted.at[idx, "title"]
        corrupted.at[idx, "title"] = title[: max(12, len(title) // 3)]
    log["operations"].append(
        {"type": "truncate_title", "count": len(truncate_indices), "indices": truncate_indices.tolist()}
    )

    stale_indices = corrupted.sample(n=min(4, len(corrupted)), random_state=19).index
    for idx in stale_indices:
        corrupted.at[idx, "published"] = "2010-01-01"
        corrupted.at[idx, "age_days"] = 5000
    log["operations"].append({"type": "stale_dates", "count": len(stale_indices), "indices": stale_indices.tolist()})

    duplicate_rows = corrupted.sample(n=min(2, len(corrupted)), random_state=23)
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    log["operations"].append({"type": "add_duplicates", "count": len(duplicate_rows)})

    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)
    write_json(output_log_path, log)
    return corrupted
