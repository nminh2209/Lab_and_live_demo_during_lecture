from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < 4:
        raise ValueError("Need at least 4 cleaned documents to build an evaluation set.")

    selected = df.sort_values("published", ascending=False).head(min(8, len(df)))
    samples: list[dict[str, Any]] = []

    for index, row in selected.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        base_id = str(index)

        samples.append(
            {
                "id": f"summary_{base_id}",
                "question_type": "summary",
                "question": f"What is the main finding of the paper titled '{title}'?",
                "ground_truth": first_sentence(row["summary"]),
                "ground_truth_doc_ids": [paper_id],
            }
        )
        samples.append(
            {
                "id": f"authors_{base_id}",
                "question_type": "authors",
                "question": f"Who authored the paper '{title}'?",
                "ground_truth": row["authors_joined"],
                "ground_truth_doc_ids": [paper_id],
            }
        )
        samples.append(
            {
                "id": f"date_{base_id}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": row["published"],
                "ground_truth_doc_ids": [paper_id],
            }
        )
        if row["categories_joined"]:
            samples.append(
                {
                    "id": f"categories_{base_id}",
                    "question_type": "categories",
                    "question": f"What categories apply to the paper '{title}'?",
                    "ground_truth": row["categories_joined"],
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(output_path, samples)
    return samples
