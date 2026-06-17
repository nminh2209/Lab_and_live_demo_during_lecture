"""Day 10 Lab — interactive demo and concept walkthrough."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import load_settings
from core.utils import read_json

st.set_page_config(
    page_title="Day 10 — RAG Pipeline Lab",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CONCEPTS = {
    "RAG": (
        "**Retrieval-Augmented Generation** combines a language model with an external knowledge base. "
        "Instead of relying only on parametric memory, the system retrieves relevant documents at query time "
        "and grounds its answers in that evidence."
    ),
    "ETL": (
        "**Extract–Transform–Load** is the backbone of this lab. We extract papers from Crossref, "
        "transform them into a clean tabular schema, and load them into ChromaDB for retrieval."
    ),
    "Embeddings": (
        "**Embeddings** map text into dense vectors so semantically similar content is close in vector space. "
        "This lab uses `all-MiniLM-L6-v2` (384 dimensions) with cosine similarity in ChromaDB."
    ),
    "Observability": (
        "**Data observability** means monitoring pipeline health: row counts, null checks, uniqueness, "
        "summary length, and freshness (`age_days`). Bad data should be detected before it reaches the agent."
    ),
    "Corruption": (
        "**Data corruption** simulates real-world failures — missing records, blank fields, noise, "
        "truncated titles, stale dates, and duplicates. We measure how each failure degrades RAG metrics "
        "and whether repair from raw source restores quality."
    ),
}


@st.cache_resource
def get_settings():
    return load_settings()


@st.cache_data
def load_json(path: str):
    return read_json(Path(path))


@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_resource
def load_index(_settings, embeddings_path: str):
    from retrieval.index import LocalEmbeddingIndex

    return LocalEmbeddingIndex.load(_settings, Path(embeddings_path))


def artifact_exists(path: Path) -> bool:
    return path.exists()


def metrics_chart(baseline: dict, corrupted: dict, repaired: dict) -> pd.DataFrame:
    keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    labels = ["Retrieval Hit Rate", "Mean Token F1", "Judge Accuracy", "Mean Judge Score"]
    rows = []
    for key, label in zip(keys, labels, strict=True):
        rows.append({"Metric": label, "Baseline": baseline.get(key, 0), "Corrupted": corrupted.get(key, 0), "Repaired": repaired.get(key, 0)})
    return pd.DataFrame(rows).set_index("Metric")


def page_overview(settings):
    st.title("Day 10: Data Pipeline & Data Observability")
    st.markdown(
        "An end-to-end **RAG pipeline** lab — from raw academic data ingestion through "
        "embedding, evaluation, observability, and corruption impact analysis."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Source API", "Crossref")
    with col2:
        st.metric("Embedding Model", "MiniLM-L6-v2")
    with col3:
        st.metric("Vector Store", "ChromaDB")

    st.subheader("Pipeline Flow")
    st.code(
        """
Crossref API  →  Raw JSON  →  Clean CSV  →  Embeddings  →  ChromaDB
                                                      ↓
                                            Test Set  →  QA / Agent
                                                      ↓
                              Quality Checks + Freshness + Metrics Report
                                                      ↓
                              Corrupt  →  Re-evaluate  →  Repair  →  Compare
        """,
        language=None,
    )

    st.subheader("Core Concepts")
    for name, text in CONCEPTS.items():
        with st.expander(name, expanded=name == "RAG"):
            st.markdown(text)

    st.info(
        "Run pipelines first: `uv run python script/run_phase1.py` then "
        "`uv run python script/run_corruption_flow.py`. "
        "Set `OPENAI_API_KEY` in `.env` for the LLM agent demo."
    )


def page_pipeline(settings):
    st.title("Pipeline Stages")
    stages = [
        (
            "1. Ingestion",
            "Fetch scholarly papers from the Crossref REST API. Parse DOI, title, abstract, "
            "authors, subjects, and dates. Save raw API response and parsed records.",
            settings.paths.raw_records_json,
            "Raw records JSON",
        ),
        (
            "2. Cleaning",
            "Filter invalid rows, normalize text, compute `age_days` and `text_for_embedding`. "
            "Deduplicate by `paper_id` and sort by publication date.",
            settings.paths.clean_csv,
            "Clean dataset CSV",
        ),
        (
            "3. Embedding & Index",
            "Encode `text_for_embedding` with MiniLM. Store vectors and metadata in ChromaDB "
            "for semantic search and exact lookup.",
            settings.paths.embeddings_json,
            "Embeddings manifest",
        ),
        (
            "4. Evaluation Set",
            "Generate factual questions (summary, authors, date, categories) with ground-truth "
            "answers tied to specific `paper_id` values.",
            settings.paths.eval_testset,
            "Test set JSON",
        ),
        (
            "5. Scoring",
            "Run retrieval + QA for each question. Compute hit rate, token F1, and LLM judge scores.",
            settings.paths.baseline_metrics,
            "Baseline metrics",
        ),
    ]

    for title, desc, path, label in stages:
        with st.expander(title, expanded=False):
            st.markdown(desc)
            if artifact_exists(path):
                st.success(f"{label} available")
                if path.suffix == ".csv":
                    st.dataframe(load_csv(str(path)).head(5), use_container_width=True)
                elif path.suffix == ".json":
                    data = load_json(str(path))
                    if isinstance(data, list):
                        st.json(data[:2])
                    else:
                        st.json(data)
            else:
                st.warning(f"Missing: `{path.name}` — run phase 1 pipeline first.")


def page_metrics(settings):
    st.title("Evaluation Metrics")
    st.markdown(
        "Compare **baseline**, **corrupted**, and **repaired** pipeline runs. "
        "Corruption should degrade metrics; repair should restore them."
    )

    paths = [
        ("Baseline", settings.paths.baseline_metrics),
        ("Corrupted", settings.paths.corrupted_metrics),
        ("Repaired", settings.paths.repaired_metrics),
    ]

    if not all(artifact_exists(p) for _, p in paths):
        st.warning("Run both pipelines to populate metrics.")
        return

    baseline = load_json(str(settings.paths.baseline_metrics))
    corrupted = load_json(str(settings.paths.corrupted_metrics))
    repaired = load_json(str(settings.paths.repaired_metrics))

    chart_df = metrics_chart(baseline, corrupted, repaired)
    st.bar_chart(chart_df, height=400)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Baseline")
        st.json(baseline)
    with c2:
        st.subheader("Corrupted")
        st.json(corrupted)
    with c3:
        st.subheader("Repaired")
        st.json(repaired)

    st.subheader("Metric Definitions")
    st.markdown(
        """
| Metric | What it measures |
|--------|------------------|
| **Retrieval hit rate** | Did top-k results include the correct `paper_id`? |
| **Mean token F1** | Token overlap between predicted and reference answer |
| **Judge accuracy** | Fraction of answers rated materially correct (1–5 scale) |
| **Mean judge score** | Average judge quality score |
        """
    )


def page_observability(settings):
    st.title("Data Observability")
    st.markdown("Automated **quality checks** and **freshness monitoring** catch bad data before it poisons the RAG system.")

    quality_files = [
        ("Baseline", settings.paths.quality_dir / "baseline_quality.json"),
        ("Corrupted", settings.paths.quality_dir / "corrupted_quality.json"),
        ("Repaired", settings.paths.quality_dir / "repaired_quality.json"),
    ]

    cols = st.columns(3)
    for col, (label, path) in zip(cols, quality_files, strict=True):
        with col:
            st.subheader(label)
            if artifact_exists(path):
                report = load_json(str(path))
                st.metric("Checks passed", f"{report['passed_checks']}/{len(report['checks'])}")
                st.metric("Overall", "PASS" if report["success"] else "FAIL")
                for check in report["checks"]:
                    icon = "✅" if check["passed"] else "❌"
                    st.write(f"{icon} `{check['name']}` = {check.get('value')}")
            else:
                st.warning("Not available")

    st.divider()
    st.subheader("Freshness Reports")
    freshness_files = [
        ("Baseline", settings.paths.freshness_report),
        ("Corrupted", settings.paths.quality_dir / "freshness_report_corrupted.json"),
        ("Repaired", settings.paths.quality_dir / "freshness_report_repaired.json"),
    ]
    fcols = st.columns(3)
    for col, (label, path) in zip(fcols, freshness_files, strict=True):
        with col:
            st.markdown(f"**{label}**")
            if artifact_exists(path):
                st.json(load_json(str(path)))
            else:
                st.caption("Not available")


def page_corruption(settings):
    st.title("Corruption Experiment")
    st.markdown(CONCEPTS["Corruption"])

    if artifact_exists(settings.paths.corruption_log):
        log = load_json(str(settings.paths.corruption_log))
        st.subheader("Operations Applied")
        for op in log.get("operations", []):
            st.markdown(f"- **{op['type']}** — count: {op.get('count', 'n/a')}")
    else:
        st.warning("Corruption log not found. Run `run_corruption_flow.py`.")

    if artifact_exists(settings.paths.clean_csv) and artifact_exists(settings.paths.corrupted_clean_csv):
        baseline_df = load_csv(str(settings.paths.clean_csv))
        corrupted_df = load_csv(str(settings.paths.corrupted_clean_csv))
        st.subheader("Dataset Size Comparison")
        st.bar_chart(
            pd.DataFrame(
                {
                    "Dataset": ["Baseline", "Corrupted", "Repaired"],
                    "Rows": [
                        len(baseline_df),
                        len(corrupted_df),
                        len(load_csv(str(settings.paths.repaired_clean_csv)))
                        if artifact_exists(settings.paths.repaired_clean_csv)
                        else 0,
                    ],
                }
            ).set_index("Dataset")
        )

    if artifact_exists(settings.paths.comparison_report):
        st.subheader("Full Comparison Report")
        st.markdown(settings.paths.comparison_report.read_text(encoding="utf-8"))


def page_demo(settings):
    st.title("Live Q&A Demo")
    st.markdown(
        "Ask questions against the indexed paper corpus. Choose a dataset version to see "
        "how corruption affects retrieval and answers."
    )

    version_map = {
        "Baseline (clean)": settings.paths.embeddings_json,
        "Corrupted": settings.paths.corrupted_embeddings_json,
        "Repaired": settings.paths.repaired_embeddings_json,
    }

    available = {k: v for k, v in version_map.items() if artifact_exists(v)}
    if not available:
        st.error("No embeddings found. Run the pipelines first.")
        return

    version = st.selectbox("Corpus version", list(available.keys()))
    use_agent = st.checkbox("Use LLM agent (requires API key)", value=False)

    test_set = []
    if artifact_exists(settings.paths.eval_testset):
        test_set = load_json(str(settings.paths.eval_testset))

    sample_questions = [item["question"] for item in test_set[:6]] if test_set else []
    default_q = sample_questions[0] if sample_questions else "Who authored the most recent paper in the corpus?"

    if sample_questions:
        picked = st.selectbox("Or pick a test question", sample_questions)
        question = st.text_area("Your question", value=picked, height=100)
    else:
        question = st.text_area("Your question", value=default_q, height=100)

    if st.button("Ask", type="primary"):
        with st.spinner("Searching corpus..."):
            from retrieval.agent import build_agent, run_agent_question
            from retrieval.qa import answer_question

            index = load_index(settings, str(available[version]))
            result = answer_question(question, settings=settings, index=index)

            st.subheader("Answer")
            st.write(result.answer)

            st.subheader("Retrieved Documents")
            for i, (doc_id, title, ctx) in enumerate(
                zip(result.retrieved_doc_ids, result.retrieved_titles, result.retrieved_contexts, strict=False),
                start=1,
            ):
                with st.expander(f"#{i} — {title[:80]}…"):
                    st.caption(f"paper_id: `{doc_id}`")
                    st.text(ctx[:600] + ("…" if len(ctx) > 600 else ""))

            if use_agent:
                try:
                    agent = build_agent(settings, index)
                    agent_answer = run_agent_question(agent, question)
                    st.subheader("Agent Answer (LLM)")
                    st.write(agent_answer)
                except Exception as exc:
                    st.error(f"Agent unavailable: {exc}")


def page_report(settings):
    st.title("Lab Report")
    detailed_path = settings.paths.baseline_report.parent / "detailed_lab_report.md"
    report_path = settings.paths.baseline_report.parent / "lab_report.md"
    if artifact_exists(detailed_path):
        st.markdown(detailed_path.read_text(encoding="utf-8"))
    elif artifact_exists(report_path):
        st.markdown(report_path.read_text(encoding="utf-8"))
    elif artifact_exists(settings.paths.baseline_report):
        st.markdown(settings.paths.baseline_report.read_text(encoding="utf-8"))
        st.caption("Showing phase 1 report. Full lab report: `data/reports/lab_report.md`")
    else:
        st.warning("Reports not generated yet.")


def main():
    settings = get_settings()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        [
            "Overview",
            "Pipeline Stages",
            "Metrics",
            "Observability",
            "Corruption",
            "Live Demo",
            "Lab Report",
        ],
    )

    st.sidebar.divider()
    st.sidebar.caption("Day 10 — Data Pipeline & Observability")
    if artifact_exists(settings.paths.baseline_metrics):
        m = load_json(str(settings.paths.baseline_metrics))
        st.sidebar.metric("Baseline hit rate", f"{m.get('retrieval_hit_rate', 0):.0%}")

    pages = {
        "Overview": page_overview,
        "Pipeline Stages": page_pipeline,
        "Metrics": page_metrics,
        "Observability": page_observability,
        "Corruption": page_corruption,
        "Live Demo": page_demo,
        "Lab Report": page_report,
    }
    pages[page](settings)


if __name__ == "__main__":
    main()
