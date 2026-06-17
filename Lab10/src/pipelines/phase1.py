from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaning produced an empty dataset. Check raw ingestion output.")

    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(df, settings=settings, embeddings_output_path=settings.paths.embeddings_json)

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)
    test_set = read_json(settings.paths.eval_testset)

    metrics_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(df, settings, report_name="baseline_quality")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(df),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics_bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    demo_questions = [item["question"] for item in test_set[:2]]
    demo_answers = []
    try:
        agent = build_agent(settings, index)
        for question in demo_questions:
            demo_answers.append(
                {
                    "question": question,
                    "agent_answer": run_agent_question(agent, question),
                    "qa_answer": answer_question(question, settings=settings, index=index).answer,
                }
            )
    except Exception as exc:
        demo_answers.append({"error": f"Agent demo skipped: {exc}"})
    write_json(settings.paths.demo_answers, demo_answers)

    print(f"Baseline pipeline complete. Clean rows: {len(df)}")
    print(f"Metrics written to: {settings.paths.baseline_metrics}")
